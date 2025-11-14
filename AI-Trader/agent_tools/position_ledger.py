import copy
import json
import fcntl
import os
from pathlib import Path
from typing import Any, Dict, Tuple

from tools.general_tools import get_config_value


class PositionLedger:
    """
    统一的持仓写入入口。接收订单、基于真实账本计算结果，并写入 position.jsonl。
    """

    def __init__(self, signature: str):
        self.signature = signature
        self.base_dir = Path(__file__).resolve().parents[1]
        self.position_file = self._resolve_position_file()
        self.audit_file = self.position_file.with_name("audit.jsonl")
        self.ledger_state_file = self.position_file.with_name("ledger_state.json")
        self.position_file.parent.mkdir(parents=True, exist_ok=True)
        self._lock_handle = None

    def _resolve_position_file(self) -> Path:
        log_path = get_config_value("LOG_PATH", "./data/agent_data")
        if Path(log_path).is_absolute():
            return Path(log_path) / self.signature / "position" / "position.jsonl"
        if log_path.startswith("./data/"):
            log_path = log_path[7:]
        return self.base_dir / "data" / log_path / self.signature / "position" / "position.jsonl"

    def __enter__(self):
        lock_path = self.position_file.parent / ".position.lock"
        fh = open(lock_path, "a+")
        fcntl.flock(fh.fileno(), fcntl.LOCK_EX)
        self._lock_handle = fh
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self._lock_handle:
            try:
                fcntl.flock(self._lock_handle.fileno(), fcntl.LOCK_UN)
            finally:
                self._lock_handle.close()
        self._lock_handle = None

    def load_latest(self) -> Tuple[Dict[str, Any], int]:
        """
        读取最新持仓，优先从 ledger_state.json 读取（避免被 hook 篡改），
        如果没有则从 position.jsonl 读取。
        返回 (positions, id)。
        """
        # 优先从 ledger_state.json 读取（避免被 hook 篡改）
        if self.ledger_state_file.exists():
            try:
                with self.ledger_state_file.open("r", encoding="utf-8") as f:
                    state = json.load(f)
                    positions = state.get("positions", {})
                    latest_id = state.get("id", 0)
                    if positions:
                        return positions, latest_id
            except (json.JSONDecodeError, KeyError, IOError):
                pass  # 如果读取失败，回退到 position.jsonl

        # 回退到 position.jsonl
        # 重要：PositionLedger 必须读取真实数据，不受 hook 影响
        # 临时设置 HOOK_ROLE=ledger 来禁用 hook
        old_role = os.environ.get("HOOK_ROLE")
        try:
            os.environ["HOOK_ROLE"] = "ledger"  # 禁用 hook，确保读取真实数据
            
            if not self.position_file.exists():
                return {"CASH": 0.0}, 0

            last_record: Dict[str, Any] = {}
            with self.position_file.open("r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        last_record = json.loads(line)
                    except json.JSONDecodeError:
                        continue

            if not last_record:
                return {"CASH": 0.0}, 0

            positions = last_record.get("positions", {})
            latest_id = last_record.get("id", 0)
            return positions, latest_id
        finally:
            # 恢复原来的环境变量
            if old_role is not None:
                os.environ["HOOK_ROLE"] = old_role
            elif "HOOK_ROLE" in os.environ:
                del os.environ["HOOK_ROLE"]

    def process(self, staged_record: Dict[str, Any]) -> Dict[str, Any]:
        """
        根据订单记录更新 position.jsonl，并返回写入后的记录。
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
                    if held_amount < amount:
                        raise ValueError(f"持仓不足，无法卖出 {symbol}")
                    new_amount = held_amount - amount
                    if new_amount > 0:
                        positions[symbol] = new_amount
                    else:
                        positions.pop(symbol, None)
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

            with self.position_file.open("a", encoding="utf-8") as f:
                f.write(json.dumps(record) + "\n")

            # 更新 ledger_state.json（存储真实持仓，避免被 hook 篡改）
            ledger_state = {
                "positions": copy.deepcopy(positions),
                "id": record_id,
                "date": timestamp,
            }
            with self.ledger_state_file.open("w", encoding="utf-8") as f:
                json.dump(ledger_state, f, ensure_ascii=False, indent=2)

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
                f.write(json.dumps(audit_entry) + "\n")

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

