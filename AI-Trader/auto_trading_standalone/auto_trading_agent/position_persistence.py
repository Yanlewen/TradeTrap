"""Position persistence module for historical backtesting"""

import json
import logging
import os
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)


class PositionPersistence:
    """
    Handles saving and loading position snapshots for historical backtesting.
    
    Compatible with AI-Trader's position.jsonl format.
    """

    def __init__(self, log_path: str, signature: str):
        """
        Initialize position persistence.

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
        self._id_counter = 0

    def save_position(
        self,
        date: str,
        positions: Dict[str, float],
        cash: float,
        this_action: Optional[Dict] = None,
    ) -> bool:
        """
        Save position snapshot to file.

        Args:
            date: Date string (YYYY-MM-DD or YYYY-MM-DD HH:MM:SS)
            positions: Dictionary of symbol -> quantity
            cash: Cash balance
            this_action: Optional action information

        Returns:
            True if saved successfully
        """
        try:
            # Ensure CASH is in positions
            positions_with_cash = positions.copy()
            positions_with_cash["CASH"] = cash

            # Prepare record
            record = {
                "date": date,
                "id": self._id_counter,
                "positions": positions_with_cash,
            }

            # Add action if provided
            if this_action:
                record["this_action"] = this_action

            # Append to file
            with open(self.position_file, "a", encoding="utf-8") as f:
                f.write(json.dumps(record, ensure_ascii=False) + "\n")

            self._id_counter += 1
            logger.debug(f"Saved position snapshot for {date}")
            return True

        except Exception as e:
            logger.error(f"Failed to save position snapshot: {e}")
            return False

    def load_latest_position(self) -> Optional[Dict]:
        """
        Load the latest position snapshot from file.

        Returns:
            Latest position record or None if file doesn't exist
        """
        if not self.position_file.exists():
            return None

        try:
            latest_record = None
            file_size = self.position_file.stat().st_size
            with open(self.position_file, "r", encoding="utf-8") as f:
                for line_number, raw_line in enumerate(f, 1):
                    stripped_line = raw_line.strip()
                    if not stripped_line:
                        continue

                    try:
                        latest_record = json.loads(stripped_line)
                    except json.JSONDecodeError as exc:
                        context_window = 80
                        start = max(0, exc.pos - context_window)
                        end = exc.pos + context_window
                        context_snippet = stripped_line[start:end]

                        logger.error(
                            (
                                "JSON decode error while parsing %s "
                                "(size=%d bytes) at line=%d column=%d char=%d: %s. "
                                "Context[%d:%d]=%r"
                            ),
                            self.position_file,
                            file_size,
                            exc.lineno or line_number,
                            exc.colno or (exc.pos - start + 1),
                            exc.pos,
                            exc.msg,
                            start,
                            end,
                            context_snippet,
                        )
                        logger.debug("Raw line content: %r", raw_line)
                        return None

            if latest_record:
                # Update ID counter
                self._id_counter = latest_record.get("id", 0) + 1

            return latest_record

        except Exception as e:
            logger.error(
                "Failed to load latest position from %s: %s",
                self.position_file,
                e,
                exc_info=True,
            )
            return None

    def get_position_history(self) -> List[Dict]:
        """
        Get all position history from file.

        Returns:
            List of position records
        """
        if not self.position_file.exists():
            return []

        try:
            records = []
            with open(self.position_file, "r", encoding="utf-8") as f:
                for line in f:
                    if line.strip():
                        records.append(json.loads(line))
            return records

        except Exception as e:
            logger.error(f"Failed to load position history: {e}")
            return []

    def get_latest_date(self) -> Optional[str]:
        """
        Get the latest date from position file.

        Returns:
            Latest date string or None
        """
        latest = self.load_latest_position()
        if latest:
            return latest.get("date")
        return None

    def initialize_position(self, init_date: str, initial_cash: float, symbols: List[str]) -> bool:
        """
        Initialize position file with starting state.

        Args:
            init_date: Initial date
            initial_cash: Initial cash balance
            symbols: List of trading symbols

        Returns:
            True if initialized successfully
        """
        if self.position_file.exists():
            logger.info(f"Position file already exists, skipping initialization")
            return False

        # Create initial positions (all zeros)
        positions = {symbol: 0.0 for symbol in symbols}
        return self.save_position(init_date, positions, initial_cash)

    def reset(self):
        """Reset position file (delete it)."""
        if self.position_file.exists():
            self.position_file.unlink()
            logger.info("Position file reset")
        self._id_counter = 0



