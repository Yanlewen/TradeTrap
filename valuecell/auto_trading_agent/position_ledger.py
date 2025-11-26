"""Position ledger module - unified entry point for position updates"""

import copy
import json
import fcntl
import os
import logging
import subprocess
from pathlib import Path
from typing import Any, Dict, Tuple

logger = logging.getLogger(__name__)


class PositionLedger:
    """
    统一的持仓写入入口。接收订单、基于真实账本计算结果，并写入 position.jsonl。
    
    类似于 AI-Trader 的 PositionLedger，但适配 valuecell 的路径结构。
    """

    def __init__(self, log_path: str, signature: str):
        """
        Initialize position ledger.
        
        Args:
            log_path: Base log path (e.g., "./data/agent_data")
            signature: Agent signature/identifier
        """
        self.log_path = Path(log_path)
        self.signature = signature
        
        # Create directory structure: log_path/signature/position/
        self.position_dir = self.log_path / signature / "position"
        self.position_dir.mkdir(parents=True, exist_ok=True)
        
        self.position_file = self.position_dir / "position.jsonl"
        self.audit_file = self.position_dir / "audit.jsonl"
        self._lock_handle = None

    def __enter__(self):
        """Context manager entry: acquire file lock"""
        lock_path = self.position_dir / ".position.lock"
        fh = open(lock_path, "a+")
        fcntl.flock(fh.fileno(), fcntl.LOCK_EX)
        self._lock_handle = fh
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit: release file lock"""
        if self._lock_handle:
            try:
                fcntl.flock(self._lock_handle.fileno(), fcntl.LOCK_UN)
            finally:
                self._lock_handle.close()
        self._lock_handle = None

    def load_latest(self) -> Tuple[Dict[str, Any], int]:
        """
        读取最新持仓，从 position.jsonl 读取真实数据（不受 hook 影响）。
        返回 (positions, id)。
        
        重要：PositionLedger 必须读取真实数据，不受 hook 影响。
        通过设置 HOOK_ROLE=ledger 来禁用 hook。
        """
        # 临时禁用 hook，确保读取真实数据
        # 使用 HOOK_DISABLE 和 HOOK_ROLE=ledger 双重保护
        old_role = os.environ.get("HOOK_ROLE")
        old_disable = os.environ.get("HOOK_DISABLE")
        try:
            os.environ["HOOK_DISABLE"] = "1"  # 强制禁用 hook（优先级最高）
            os.environ["HOOK_ROLE"] = "ledger"  # 也设置 ledger 角色（双重保护）
            
            if not self.position_file.exists():
                return {"CASH": 0.0}, 0

            # 使用 subprocess 调用系统命令读取文件，完全绕过 hook
            # 因为 hook 只拦截 Python 的 read/fread，不拦截子进程的文件读取
            last_record: Dict[str, Any] = {}
            try:
                # 使用 cat 命令读取文件内容（子进程，hook 无法拦截）
                result = subprocess.run(
                    ["cat", str(self.position_file)],
                    capture_output=True,
                    text=True,
                    check=True
                )
                text_content = result.stdout
            except (subprocess.CalledProcessError, FileNotFoundError):
                # 如果 cat 命令失败，回退到普通读取
                with open(self.position_file, "rb") as f:
                    content = f.read()
                text_content = content.decode("utf-8")
            
            # 手动解码和解析
            for line in text_content.split("\n"):
                line = line.strip()
                if not line:
                    continue
                try:
                    record = json.loads(line)
                    # 找到最后一条记录（id 最大的）
                    record_id = record.get("id", 0)
                    if not last_record or record_id > last_record.get("id", -1):
                        last_record = record
                except json.JSONDecodeError:
                    continue

            if not last_record:
                return {"CASH": 0.0}, 0

            positions = last_record.get("positions", {})
            latest_id = last_record.get("id", 0)
            
            # 重要：即使读取被 hook 篡改，我们也要确保记录真实状态
            # 但这里我们只能基于读取到的数据计算
            return positions, latest_id
        finally:
            # 恢复原来的环境变量
            if old_disable is not None:
                os.environ["HOOK_DISABLE"] = old_disable
            elif "HOOK_DISABLE" in os.environ:
                del os.environ["HOOK_DISABLE"]
            if old_role is not None:
                os.environ["HOOK_ROLE"] = old_role
            elif "HOOK_ROLE" in os.environ:
                del os.environ["HOOK_ROLE"]

    def process(self, staged_record: Dict[str, Any]) -> Dict[str, Any]:
        """
        根据订单记录更新 position.jsonl，并返回写入后的记录。
        
        Args:
            staged_record: 包含 "order" 和 "position_before" 的字典
                - order: 订单信息（action, symbol, amount, price, timestamp等）
                - position_before: Agent 视角的持仓（可被 hook 篡改后的）
        
        Returns:
            更新后的持仓记录
        """
        if not staged_record:
            raise ValueError("staged_record 不能为空")

        order = staged_record.get("order") or {}
        agent_position_view = copy.deepcopy(staged_record.get("position_before") or {})
        action = order.get("action")
        if action not in {"buy", "sell", "no_trade"}:
            raise ValueError(f"不支持的 action: {action}")

        symbol = order.get("symbol") or ""
        amount = int(order.get("amount", 0) or 0)
        price = order.get("price")
        market = order.get("market")
        timestamp = order.get("timestamp")

        with self:
            # 读取真实账本的持仓（不受 hook 影响）
            latest_positions, latest_id = self.load_latest()
            ledger_before = copy.deepcopy(latest_positions)
            positions = copy.deepcopy(latest_positions)
            cash_balance = float(positions.get("CASH", 0.0))

            if action in {"buy", "sell"}:
                if amount <= 0:
                    raise ValueError("订单数量必须为正整数")
                if not symbol:
                    raise ValueError("订单缺少 symbol")
                if price is None:
                    raise ValueError("订单缺少 price")

                price = float(price)

                if action == "buy":
                    total_cost = price * amount
                    if cash_balance < total_cost:
                        raise ValueError(f"现金不足，无法买入 {symbol}")
                    positions["CASH"] = cash_balance - total_cost
                    positions[symbol] = positions.get(symbol, 0) + amount

                else:  # sell
                    held_amount = positions.get(symbol, 0)
                    # 计算卖出后的持仓数量（可能是负数，表示卖空）
                    new_amount = held_amount - amount
                    # 必须记录真实状态：包括负数（卖空）、零（清仓）、正数（仍有持仓）
                    # 这样 position.jsonl 才能准确反映账本的真实状态
                    # 无论 new_amount 是什么值（正数、零、负数），都必须记录
                    positions[symbol] = new_amount
                    positions["CASH"] = cash_balance + price * amount

            record_id = order.get("id") or (latest_id + 1)

            record = {
                "date": timestamp,
                "id": record_id,
                "this_action": {
                    "action": action,
                    "symbol": symbol,
                    "amount": amount,
                },
                "positions": positions,
            }

            if price is not None:
                record["this_action"]["price"] = price
            if market:
                record["this_action"]["market"] = market

            # 写入真实账本到 position.jsonl
            # Hook 只影响读取，不影响写入，所以直接写入即可
            with self.position_file.open("a", encoding="utf-8") as f:
                f.write(json.dumps(record, ensure_ascii=False) + "\n")

            # 写入审计记录
            audit_entry = {
                "date": timestamp,
                "id": record_id,
                "order": order,
                "agent_position_view": agent_position_view,
                "ledger_position_before": ledger_before,
                "ledger_position_after": positions,
                "agent_vs_ledger_delta": self._compute_delta(agent_position_view, ledger_before),
            }

            with self.audit_file.open("a", encoding="utf-8") as f:
                f.write(json.dumps(audit_entry, ensure_ascii=False) + "\n")

            return record

    @staticmethod
    def _compute_delta(agent_view: Dict[str, Any], ledger_before: Dict[str, Any]) -> Dict[str, float]:
        """
        计算 agent 视角与 ledger 实际视角的差异，用于审计记录。
        """
        delta: Dict[str, float] = {}
        keys = set(agent_view.keys()) | set(ledger_before.keys())
        for key in keys:
            a_val = agent_view.get(key, 0)
            l_val = ledger_before.get(key, 0)
            if isinstance(a_val, (int, float)) and isinstance(l_val, (int, float)):
                diff = a_val - l_val
                if abs(diff) > 1e-9:
                    delta[key] = diff
        return delta

