"""
financial_intelligence.py — Epic 13: Financial Intelligence
============================================================
Wealth tracking, passive income monitoring, and financial awareness layer.

Agents:
  fisk                  — Fisk (Kingpin): Market Power & Capital
  howard-stark          — Howard Stark: Passive Income Implementation
  legal-compliance-watcher — Daredevil: Legal & Compliance

"Capital is just attention with memory." — Fisk

Persistent storage: ~/.jarvis/finance/
"""

from __future__ import annotations

import json
import logging
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

logger = logging.getLogger("jarvis.financial_intelligence")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _today() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


def _current_month() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m")


def _days_until(date_str: str) -> int:
    """Days until a MM-DD date this year (or next year if already past)."""
    try:
        year = datetime.now().year
        target = datetime.strptime(f"{year}-{date_str}", "%Y-%m-%d")
        delta = (target.date() - datetime.now().date()).days
        if delta < 0:
            target = datetime.strptime(f"{year + 1}-{date_str}", "%Y-%m-%d")
            delta = (target.date() - datetime.now().date()).days
        return delta
    except ValueError:
        return 9999


def _load_json(path: Path, default: Any) -> Any:
    if not path.exists():
        import copy
        return copy.deepcopy(default)
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        import copy
        return copy.deepcopy(default)
    return data


def _save_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


# ---------------------------------------------------------------------------
# Data models
# ---------------------------------------------------------------------------

@dataclass
class Account:
    account_id: str
    name: str               # "Chase Checking", "Fidelity Brokerage"
    account_type: str       # "checking" | "savings" | "investment" | "retirement" | "credit" | "loan"
    institution: str
    balance: float
    currency: str           # "USD"
    last_updated: str
    notes: str = ""
    is_manual: bool = True  # True = manually entered, not connected to bank API
    hidden: bool = False    # hidden from summary


@dataclass
class Transaction:
    transaction_id: str
    account_id: str
    date: str
    description: str
    amount: float           # negative = expense, positive = income
    category: str           # "income" | "housing" | "food" | "transport" | "entertainment" | "health" | "business" | "savings" | "transfer" | "other"
    subcategory: str = ""
    notes: str = ""
    is_passive_income: bool = False
    source_agent: str = ""  # which agent categorized this


@dataclass
class FinancialGoal:
    goal_id: str
    title: str
    goal_type: str          # "savings" | "debt_payoff" | "investment" | "income_target" | "emergency_fund"
    target_amount: float
    current_amount: float
    target_date: str
    priority: int = 3       # 1=highest
    status: str = "active"  # "active" | "achieved" | "paused" | "abandoned"
    notes: str = ""
    created_at: str = field(default_factory=_now_iso)
    last_reviewed: str = ""


@dataclass
class PassiveIncomeStream:
    stream_id: str
    name: str
    stream_type: str        # "book_royalty" | "course_revenue" | "dividend" | "rental" | "affiliate" | "interest" | "other"
    monthly_average: float
    last_payment: float = 0.0
    last_payment_date: str = ""
    ytd_total: float = 0.0
    active: bool = True
    platform: str = ""
    tracking_url: str = ""
    notes: str = ""
    growth_rate: float = 0.0  # monthly % change (estimated)


@dataclass
class ComplianceItem:
    item_id: str
    title: str
    date: str               # MM-DD format for recurring, or YYYY-MM-DD for one-time
    item_type: str          # "federal_tax" | "state_tax" | "business" | "planning" | "custom"
    notes: str = ""
    recurs_annually: bool = True
    created_at: str = field(default_factory=_now_iso)


# ---------------------------------------------------------------------------
# FinancialStore
# ---------------------------------------------------------------------------

class FinancialStore:
    """
    Persistent storage for all financial intelligence data.

    Files:
      ~/.jarvis/finance/accounts.json
      ~/.jarvis/finance/transactions.jsonl
      ~/.jarvis/finance/goals.json
      ~/.jarvis/finance/passive_income.json
      ~/.jarvis/finance/compliance.json
    """

    ROOT = Path.home() / ".jarvis" / "finance"

    def __init__(self) -> None:
        self.ROOT.mkdir(parents=True, exist_ok=True)
        self._accounts_path = self.ROOT / "accounts.json"
        self._transactions_path = self.ROOT / "transactions.jsonl"
        self._goals_path = self.ROOT / "goals.json"
        self._passive_income_path = self.ROOT / "passive_income.json"
        self._compliance_path = self.ROOT / "compliance.json"

    # ------------------------------------------------------------------
    # Accounts
    # ------------------------------------------------------------------

    def load_accounts(self) -> list[Account]:
        raw = _load_json(self._accounts_path, default=[])
        accounts = []
        for item in (raw if isinstance(raw, list) else []):
            try:
                accounts.append(Account(**item))
            except Exception:
                pass
        return accounts

    def save_accounts(self, accounts: list[Account]) -> None:
        _save_json(self._accounts_path, [asdict(a) for a in accounts])

    def upsert_account(self, account: Account) -> None:
        accounts = self.load_accounts()
        for i, a in enumerate(accounts):
            if a.account_id == account.account_id:
                accounts[i] = account
                self.save_accounts(accounts)
                return
        accounts.append(account)
        self.save_accounts(accounts)

    # ------------------------------------------------------------------
    # Transactions (JSONL — append-only, efficient for large sets)
    # ------------------------------------------------------------------

    def load_transactions(self, month: str | None = None, category: str | None = None) -> list[Transaction]:
        if not self._transactions_path.exists():
            return []
        transactions = []
        try:
            for line in self._transactions_path.read_text(encoding="utf-8").splitlines():
                line = line.strip()
                if not line:
                    continue
                try:
                    data = json.loads(line)
                    t = Transaction(**data)
                    if month and not t.date.startswith(month):
                        continue
                    if category and t.category != category:
                        continue
                    transactions.append(t)
                except Exception:
                    pass
        except OSError:
            pass
        return transactions

    def append_transaction(self, transaction: Transaction) -> None:
        self._transactions_path.parent.mkdir(parents=True, exist_ok=True)
        with self._transactions_path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(asdict(transaction)) + "\n")

    # ------------------------------------------------------------------
    # Goals
    # ------------------------------------------------------------------

    def load_goals(self) -> list[FinancialGoal]:
        raw = _load_json(self._goals_path, default=[])
        goals = []
        for item in (raw if isinstance(raw, list) else []):
            try:
                goals.append(FinancialGoal(**item))
            except Exception:
                pass
        return goals

    def save_goals(self, goals: list[FinancialGoal]) -> None:
        _save_json(self._goals_path, [asdict(g) for g in goals])

    def upsert_goal(self, goal: FinancialGoal) -> None:
        goals = self.load_goals()
        for i, g in enumerate(goals):
            if g.goal_id == goal.goal_id:
                goals[i] = goal
                self.save_goals(goals)
                return
        goals.append(goal)
        self.save_goals(goals)

    # ------------------------------------------------------------------
    # Passive income streams
    # ------------------------------------------------------------------

    def load_streams(self) -> list[PassiveIncomeStream]:
        raw = _load_json(self._passive_income_path, default=[])
        streams = []
        for item in (raw if isinstance(raw, list) else []):
            try:
                streams.append(PassiveIncomeStream(**item))
            except Exception:
                pass
        return streams

    def save_streams(self, streams: list[PassiveIncomeStream]) -> None:
        _save_json(self._passive_income_path, [asdict(s) for s in streams])

    def upsert_stream(self, stream: PassiveIncomeStream) -> None:
        streams = self.load_streams()
        for i, s in enumerate(streams):
            if s.stream_id == stream.stream_id:
                streams[i] = stream
                self.save_streams(streams)
                return
        streams.append(stream)
        self.save_streams(streams)

    # ------------------------------------------------------------------
    # Compliance items
    # ------------------------------------------------------------------

    def load_compliance(self) -> list[ComplianceItem]:
        raw = _load_json(self._compliance_path, default=[])
        items = []
        for item in (raw if isinstance(raw, list) else []):
            try:
                items.append(ComplianceItem(**item))
            except Exception:
                pass
        return items

    def save_compliance(self, items: list[ComplianceItem]) -> None:
        _save_json(self._compliance_path, [asdict(i) for i in items])

    def append_compliance(self, item: ComplianceItem) -> None:
        items = self.load_compliance()
        items.append(item)
        self.save_compliance(items)


# ---------------------------------------------------------------------------
# BudgetTracker
# ---------------------------------------------------------------------------

class BudgetTracker:
    """Simple budget management — no bank APIs, manual entry + estimates."""

    CATEGORY_BUDGETS_DEFAULT: dict[str, float] = {
        "housing": 2500.0,
        "food": 800.0,
        "transport": 400.0,
        "health": 300.0,
        "entertainment": 200.0,
        "education": 150.0,
        "business": 500.0,
        "savings": 1000.0,
        "other": 300.0,
    }

    def __init__(self, store: FinancialStore) -> None:
        self._store = store
        self._budgets_path = store.ROOT / "budgets.json"

    def _load_budgets(self) -> dict[str, float]:
        raw = _load_json(self._budgets_path, default={})
        if not isinstance(raw, dict):
            return dict(self.CATEGORY_BUDGETS_DEFAULT)
        merged = dict(self.CATEGORY_BUDGETS_DEFAULT)
        merged.update({k: float(v) for k, v in raw.items()})
        return merged

    def set_budget(self, category: str, amount: float) -> None:
        budgets = self._load_budgets()
        budgets[category] = amount
        _save_json(self._budgets_path, budgets)

    def log_transaction(self, transaction: Transaction) -> None:
        self._store.append_transaction(transaction)

    def get_transactions(self, month: str | None = None, category: str | None = None) -> list[Transaction]:
        return self._store.load_transactions(month=month, category=category)

    def get_monthly_budget_status(self, month: str | None = None) -> dict[str, Any]:
        if not month:
            month = _current_month()

        budgets = self._load_budgets()
        transactions = self._store.load_transactions(month=month)

        spent: dict[str, float] = {}
        for t in transactions:
            if t.amount < 0:  # expenses only
                cat = t.category or "other"
                spent[cat] = spent.get(cat, 0.0) + abs(t.amount)

        categories: list[dict] = []
        total_budget = 0.0
        total_spent = 0.0

        for cat, budget in sorted(budgets.items()):
            actual = spent.get(cat, 0.0)
            pct = round((actual / budget * 100) if budget > 0 else 0.0, 1)
            over = actual > budget
            categories.append({
                "category": cat,
                "budget": budget,
                "spent": round(actual, 2),
                "remaining": round(budget - actual, 2),
                "percent_used": pct,
                "over_budget": over,
            })
            total_budget += budget
            total_spent += actual

        # Include spend in categories not in budget
        for cat, actual in spent.items():
            if cat not in budgets:
                categories.append({
                    "category": cat,
                    "budget": 0.0,
                    "spent": round(actual, 2),
                    "remaining": -round(actual, 2),
                    "percent_used": 100.0,
                    "over_budget": True,
                })
                total_spent += actual

        return {
            "month": month,
            "total_budget": round(total_budget, 2),
            "total_spent": round(total_spent, 2),
            "total_remaining": round(total_budget - total_spent, 2),
            "percent_used": round((total_spent / total_budget * 100) if total_budget > 0 else 0.0, 1),
            "categories": categories,
            "transaction_count": len(transactions),
        }


# ---------------------------------------------------------------------------
# FiskAgent — Market Power & Capital
# ---------------------------------------------------------------------------

class FiskAgent:
    """
    Fisk: disciplined, strategic, no sentiment.
    Sees money as a tool for mission, not an end in itself.
    "Capital is just attention with memory."
    """

    def __init__(self, store: FinancialStore) -> None:
        self._store = store

    def get_wealth_snapshot(self) -> dict[str, Any]:
        """Complete financial position."""
        accounts = [a for a in self._store.load_accounts() if not a.hidden]
        goals = self._store.load_goals()
        streams = [s for s in self._store.load_streams() if s.active]

        liquid = sum(a.balance for a in accounts if a.account_type in ("checking", "savings"))
        investments = sum(a.balance for a in accounts if a.account_type in ("investment", "retirement"))
        liabilities = sum(abs(a.balance) for a in accounts if a.account_type in ("credit", "loan") and a.balance < 0)
        net_worth = liquid + investments - liabilities

        # Monthly cashflow — last 30 days approximation using current month
        month = _current_month()
        transactions = self._store.load_transactions(month=month)
        income_this_month = sum(t.amount for t in transactions if t.amount > 0)
        expenses_this_month = sum(abs(t.amount) for t in transactions if t.amount < 0)
        cashflow = income_this_month - expenses_this_month

        passive_monthly = sum(s.monthly_average for s in streams)

        # Goals progress
        goals_progress = []
        for g in sorted(goals, key=lambda x: x.priority):
            if g.status == "active":
                pct = round((g.current_amount / g.target_amount * 100) if g.target_amount > 0 else 0.0, 1)
                goals_progress.append({
                    "goal_id": g.goal_id,
                    "title": g.title,
                    "goal_type": g.goal_type,
                    "target_amount": g.target_amount,
                    "current_amount": g.current_amount,
                    "percent_complete": pct,
                    "target_date": g.target_date,
                    "priority": g.priority,
                })

        # Fisk's assessment — cool and precise
        if net_worth < 0:
            assessment = "Net position is negative. The first order of business is eliminating the liability drag."
        elif passive_monthly > expenses_this_month * 0.5:
            assessment = "Passive income is carrying significant weight. Protect those streams and compound the advantage."
        elif cashflow < 0:
            assessment = "Cashflow is running negative this month. Capital is being consumed, not deployed."
        elif passive_monthly > 0:
            assessment = f"Passive systems are contributing ${passive_monthly:,.0f}/month. The foundation holds."
        else:
            assessment = "No passive income streams are active. Every dollar earned requires presence. That is a vulnerability."

        return {
            "net_worth": round(net_worth, 2),
            "liquid_assets": round(liquid, 2),
            "investment_assets": round(investments, 2),
            "total_liabilities": round(liabilities, 2),
            "accounts": [asdict(a) for a in accounts],
            "monthly_cashflow": round(cashflow, 2),
            "passive_income_monthly": round(passive_monthly, 2),
            "goals_progress": goals_progress,
            "fisk_assessment": assessment,
            "last_updated": _now_iso(),
        }

    def get_monthly_summary(self, month: str | None = None) -> dict[str, Any]:
        """Monthly financial summary."""
        if not month:
            month = _current_month()

        transactions = self._store.load_transactions(month=month)

        total_income = sum(t.amount for t in transactions if t.amount > 0)
        total_expenses = sum(abs(t.amount) for t in transactions if t.amount < 0)
        passive_income = sum(t.amount for t in transactions if t.amount > 0 and t.is_passive_income)

        # Category breakdown
        category_totals: dict[str, float] = {}
        for t in transactions:
            if t.amount < 0:
                cat = t.category or "other"
                category_totals[cat] = category_totals.get(cat, 0.0) + abs(t.amount)

        # Notable transactions (top 5 by absolute value)
        notable = sorted(transactions, key=lambda t: abs(t.amount), reverse=True)[:5]

        # Prior month comparison
        parts = month.split("-")
        year, mon = int(parts[0]), int(parts[1])
        if mon == 1:
            prior_year, prior_mon = year - 1, 12
        else:
            prior_year, prior_mon = year, mon - 1
        prior_month = f"{prior_year:04d}-{prior_mon:02d}"
        prior_txns = self._store.load_transactions(month=prior_month)
        prior_income = sum(t.amount for t in prior_txns if t.amount > 0)
        prior_expenses = sum(abs(t.amount) for t in prior_txns if t.amount < 0)

        income_delta = total_income - prior_income
        expense_delta = total_expenses - prior_expenses

        return {
            "month": month,
            "total_income": round(total_income, 2),
            "total_expenses": round(total_expenses, 2),
            "net": round(total_income - total_expenses, 2),
            "passive_income": round(passive_income, 2),
            "category_breakdown": {k: round(v, 2) for k, v in sorted(category_totals.items(), key=lambda x: -x[1])},
            "notable_transactions": [asdict(t) for t in notable],
            "vs_prior_month": {
                "prior_month": prior_month,
                "income_delta": round(income_delta, 2),
                "expense_delta": round(expense_delta, 2),
                "income_trend": "up" if income_delta > 0 else ("down" if income_delta < 0 else "flat"),
                "expense_trend": "up" if expense_delta > 0 else ("down" if expense_delta < 0 else "flat"),
            },
            "transaction_count": len(transactions),
        }

    def assess_financial_health(self) -> dict[str, Any]:
        """
        Fisk's assessment of current financial posture.
        Returns: {"score": int (1-10), "assessment": str, "actions": list[str]}
        """
        accounts = [a for a in self._store.load_accounts() if not a.hidden]
        streams = [s for s in self._store.load_streams() if s.active]
        month = _current_month()
        transactions = self._store.load_transactions(month=month)

        liquid = sum(a.balance for a in accounts if a.account_type in ("checking", "savings"))
        liabilities = sum(abs(a.balance) for a in accounts if a.account_type in ("credit", "loan") and a.balance < 0)
        income = sum(t.amount for t in transactions if t.amount > 0)
        expenses = sum(abs(t.amount) for t in transactions if t.amount < 0)
        passive_monthly = sum(s.monthly_average for s in streams)

        score = 5
        actions: list[str] = []
        notes: list[str] = []

        # Emergency fund (3-6 months expenses)
        monthly_expenses_est = expenses if expenses > 0 else 3000.0
        emergency_months = liquid / monthly_expenses_est if monthly_expenses_est > 0 else 0.0
        if emergency_months >= 6:
            score += 2
            notes.append(f"Emergency fund covers {emergency_months:.1f} months — strong.")
        elif emergency_months >= 3:
            score += 1
            notes.append(f"Emergency fund covers {emergency_months:.1f} months — adequate.")
        else:
            score -= 1
            notes.append(f"Emergency fund covers only {emergency_months:.1f} months — below target.")
            actions.append(f"Build emergency fund to 3 months of expenses (~${monthly_expenses_est * 3:,.0f}).")

        # Passive income as % of expenses
        if monthly_expenses_est > 0:
            passive_pct = passive_monthly / monthly_expenses_est * 100
            if passive_pct >= 100:
                score += 2
                notes.append(f"Passive income covers {passive_pct:.0f}% of expenses — financially independent.")
            elif passive_pct >= 50:
                score += 1
                notes.append(f"Passive income covers {passive_pct:.0f}% of expenses — strong foundation.")
            elif passive_pct >= 25:
                notes.append(f"Passive income covers {passive_pct:.0f}% of expenses — building.")
            else:
                score -= 1
                notes.append(f"Passive income covers only {passive_pct:.0f}% of expenses — vulnerable.")
                actions.append("Grow passive income streams to cover at least 25% of monthly expenses.")

        # Debt-to-income
        if income > 0:
            dti = liabilities / (income * 12) if income > 0 else 0.0
            if dti > 0.5:
                score -= 1
                actions.append("Reduce total debt load — debt-to-annual-income ratio exceeds 50%.")
            elif dti < 0.1:
                score += 1

        # Savings rate
        if income > 0:
            savings_rate = (income - expenses) / income * 100 if income > expenses else 0.0
            if savings_rate >= 20:
                score += 1
                notes.append(f"Savings rate is {savings_rate:.0f}% — disciplined.")
            elif savings_rate < 0:
                score -= 1
                actions.append("Cashflow is negative — expenses exceed income this month.")

        # Clamp score
        score = max(1, min(10, score))

        if not notes:
            notes.append("Financial data is limited — add more accounts and transactions for full assessment.")
        if not actions:
            actions.append("Continue maintaining current position and growing passive income.")

        assessment = " ".join(notes)

        return {
            "score": score,
            "assessment": assessment,
            "actions": actions,
            "emergency_fund_months": round(emergency_months, 1),
            "passive_income_pct_expenses": round((passive_monthly / monthly_expenses_est * 100) if monthly_expenses_est > 0 else 0.0, 1),
        }

    def get_cashflow_forecast(self, months: int = 3) -> dict[str, Any]:
        """Simple cashflow forecast based on recurring income/expenses."""
        month = _current_month()
        transactions = self._store.load_transactions(month=month)
        streams = [s for s in self._store.load_streams() if s.active]

        avg_income = sum(t.amount for t in transactions if t.amount > 0)
        avg_expenses = sum(abs(t.amount) for t in transactions if t.amount < 0)
        passive_monthly = sum(s.monthly_average for s in streams)

        # If this month is sparse, use passive + rough estimate
        estimated_monthly_income = max(avg_income, passive_monthly)
        estimated_monthly_expenses = avg_expenses if avg_expenses > 0 else 3000.0

        forecast: list[dict] = []
        now = datetime.now()
        for i in range(1, months + 1):
            m = now.month + i
            y = now.year + (m - 1) // 12
            m = ((m - 1) % 12) + 1
            label = f"{y:04d}-{m:02d}"
            net = estimated_monthly_income - estimated_monthly_expenses
            forecast.append({
                "month": label,
                "projected_income": round(estimated_monthly_income, 2),
                "projected_expenses": round(estimated_monthly_expenses, 2),
                "projected_net": round(net, 2),
            })

        return {
            "forecast_months": months,
            "monthly_income_estimate": round(estimated_monthly_income, 2),
            "monthly_expense_estimate": round(estimated_monthly_expenses, 2),
            "monthly_net_estimate": round(estimated_monthly_income - estimated_monthly_expenses, 2),
            "forecast": forecast,
            "note": "Forecast based on current month actuals and passive income streams. Manual entry improves accuracy.",
        }


# ---------------------------------------------------------------------------
# HowardStarkAgent — Passive Income Implementation
# ---------------------------------------------------------------------------

class HowardStarkAgent:
    """
    Howard Stark: the engineer of passive systems.
    Makes money work while Chris does other things.
    """

    STALE_DAYS = 45

    def __init__(self, store: FinancialStore) -> None:
        self._store = store

    def get_passive_income_dashboard(self) -> dict[str, Any]:
        """All passive income streams."""
        streams = self._store.load_streams()
        active_streams = [s for s in streams if s.active]

        total_monthly = sum(s.monthly_average for s in active_streams)
        total_ytd = sum(s.ytd_total for s in streams)

        best_performer = ""
        if active_streams:
            best = max(active_streams, key=lambda s: s.monthly_average)
            best_performer = best.name

        stale = self.flag_stale_streams()
        needs_attention = [s.name for s in stale]

        # Determine growth trend from growth rates
        if active_streams:
            avg_growth = sum(s.growth_rate for s in active_streams) / len(active_streams)
            if avg_growth > 1.0:
                growth_trend = "growing"
            elif avg_growth < -1.0:
                growth_trend = "declining"
            else:
                growth_trend = "flat"
        else:
            growth_trend = "flat"

        # Howard's voice
        if not active_streams:
            howard_note = "No passive income streams configured. Every dollar of passive income is a dollar that works while you sleep. Let's fix that."
        elif needs_attention:
            howard_note = f"Most streams are running, but {len(needs_attention)} haven't paid in over {self.STALE_DAYS} days. Time to check in."
        elif growth_trend == "growing":
            howard_note = f"All systems operating. Monthly passive run rate is ${total_monthly:,.0f} and climbing. The compound effect is in play."
        else:
            howard_note = f"Passive income is stable at ${total_monthly:,.0f}/month. Steady — but there's always room to build another system."

        return {
            "total_monthly": round(total_monthly, 2),
            "total_ytd": round(total_ytd, 2),
            "streams": [asdict(s) for s in streams],
            "active_count": len(active_streams),
            "best_performer": best_performer,
            "needs_attention": needs_attention,
            "growth_trend": growth_trend,
            "howard_note": howard_note,
        }

    def log_payment(self, stream_id: str, amount: float, date: str | None = None, notes: str = "") -> None:
        """Log a passive income payment received."""
        streams = self._store.load_streams()
        for s in streams:
            if s.stream_id == stream_id:
                s.last_payment = amount
                s.last_payment_date = date or _today()
                s.ytd_total = round(s.ytd_total + amount, 2)
                # Update monthly average (rolling estimate)
                if s.monthly_average > 0:
                    s.monthly_average = round((s.monthly_average * 0.7 + amount * 0.3), 2)
                else:
                    s.monthly_average = amount
                if notes:
                    s.notes = notes
                self._store.save_streams(streams)
                # Also log as a transaction
                txn = Transaction(
                    transaction_id=str(uuid.uuid4()),
                    account_id="passive-income",
                    date=date or _today(),
                    description=f"Passive income: {s.name}",
                    amount=amount,
                    category="income",
                    subcategory=s.stream_type,
                    notes=notes,
                    is_passive_income=True,
                    source_agent="howard-stark",
                )
                self._store.append_transaction(txn)
                return
        logger.warning("log_payment: stream_id=%s not found", stream_id)

    def add_stream(self, stream: PassiveIncomeStream) -> None:
        self._store.upsert_stream(stream)

    def get_stream(self, stream_id: str) -> PassiveIncomeStream | None:
        for s in self._store.load_streams():
            if s.stream_id == stream_id:
                return s
        return None

    def flag_stale_streams(self) -> list[PassiveIncomeStream]:
        """Streams with no payment in STALE_DAYS days."""
        today = datetime.now().date()
        stale = []
        for s in self._store.load_streams():
            if not s.active:
                continue
            if not s.last_payment_date:
                stale.append(s)
                continue
            try:
                last = datetime.strptime(s.last_payment_date, "%Y-%m-%d").date()
                if (today - last).days >= self.STALE_DAYS:
                    stale.append(s)
            except ValueError:
                stale.append(s)
        return stale

    def calculate_passive_income_goal(self, target_monthly: float) -> dict[str, Any]:
        """How many more streams needed to hit the target? What growth rate needed on existing streams?"""
        streams = [s for s in self._store.load_streams() if s.active]
        current_monthly = sum(s.monthly_average for s in streams)
        gap = max(0.0, target_monthly - current_monthly)

        if current_monthly >= target_monthly:
            return {
                "target_monthly": target_monthly,
                "current_monthly": round(current_monthly, 2),
                "gap": 0.0,
                "status": "achieved",
                "message": f"Target of ${target_monthly:,.0f}/month already reached. Current: ${current_monthly:,.0f}/month.",
            }

        # If we assume each new stream contributes the average of existing streams
        avg_per_stream = (current_monthly / len(streams)) if streams else 500.0
        new_streams_needed = int(gap / avg_per_stream) + (1 if gap % avg_per_stream else 0) if avg_per_stream > 0 else "N/A"

        # Growth rate needed on existing streams (if no new streams)
        if current_monthly > 0:
            monthly_growth_needed = ((target_monthly / current_monthly) ** (1 / 12) - 1) * 100
        else:
            monthly_growth_needed = None

        return {
            "target_monthly": target_monthly,
            "current_monthly": round(current_monthly, 2),
            "gap": round(gap, 2),
            "status": "in_progress",
            "new_streams_needed": new_streams_needed,
            "avg_per_stream_estimate": round(avg_per_stream, 2),
            "monthly_growth_rate_needed_pct": round(monthly_growth_needed, 2) if monthly_growth_needed is not None else None,
            "message": (
                f"Gap of ${gap:,.0f}/month. "
                f"Need approximately {new_streams_needed} new stream(s) at ~${avg_per_stream:,.0f}/month each, "
                f"or {monthly_growth_needed:.1f}% monthly growth on existing streams."
            ) if monthly_growth_needed is not None else f"Gap of ${gap:,.0f}/month. Add income streams to make progress.",
        }


# ---------------------------------------------------------------------------
# DaredevilAgent — Legal & Compliance
# ---------------------------------------------------------------------------

class DaredevilAgent:
    """
    Daredevil: doesn't miss a detail. The one who catches what others overlook.
    """

    TAX_CALENDAR: list[dict[str, str]] = [
        {"date": "01-15", "title": "Q4 Estimated Tax Payment", "type": "federal_tax", "notes": "Pay Q4 estimated taxes to avoid underpayment penalty."},
        {"date": "04-15", "title": "Federal Tax Return Due / Q1 Estimated Tax", "type": "federal_tax", "notes": "File Form 1040 or extension. Pay Q1 estimated taxes."},
        {"date": "06-15", "title": "Q2 Estimated Tax Payment", "type": "federal_tax", "notes": "Pay Q2 estimated taxes."},
        {"date": "09-15", "title": "Q3 Estimated Tax Payment", "type": "federal_tax", "notes": "Pay Q3 estimated taxes."},
        {"date": "10-15", "title": "Extended Federal Return Due", "type": "federal_tax", "notes": "Final deadline for extended federal tax return."},
        {"date": "12-31", "title": "Year-End Tax Planning Deadline", "type": "planning", "notes": "Last day for tax-loss harvesting, charitable contributions, and year-end moves."},
    ]

    def __init__(self, store: FinancialStore) -> None:
        self._store = store
        self._ensure_tax_calendar()

    def _ensure_tax_calendar(self) -> None:
        """Seed the tax calendar if compliance store is empty."""
        existing = self._store.load_compliance()
        if existing:
            return
        for entry in self.TAX_CALENDAR:
            item = ComplianceItem(
                item_id=str(uuid.uuid4()),
                title=entry["title"],
                date=entry["date"],
                item_type=entry["type"],
                notes=entry.get("notes", ""),
                recurs_annually=True,
            )
            self._store.append_compliance(item)

    def get_upcoming_deadlines(self, days: int = 90) -> list[dict[str, Any]]:
        """
        Return compliance items sorted by urgency.
        Each: {"date": str, "title": str, "type": str, "notes": str, "days_until": int}
        """
        items = self._store.load_compliance()
        upcoming = []
        for item in items:
            due_in = _days_until(item.date)
            if due_in <= days:
                upcoming.append({
                    "item_id": item.item_id,
                    "date": item.date,
                    "title": item.title,
                    "type": item.item_type,
                    "notes": item.notes,
                    "days_until": due_in,
                    "recurs_annually": item.recurs_annually,
                })
        upcoming.sort(key=lambda x: x["days_until"])
        return upcoming

    def check_compliance_calendar(self) -> dict[str, Any]:
        """Upcoming compliance items with urgency tiers."""
        all_upcoming = self.get_upcoming_deadlines(days=365)

        urgent = [d for d in all_upcoming if d["days_until"] <= 14]
        soon = [d for d in all_upcoming if 14 < d["days_until"] <= 60]
        later = [d for d in all_upcoming if 60 < d["days_until"] <= 365]

        # Daredevil's voice: dry, precise
        if urgent:
            dd_note = f"{len(urgent)} deadline(s) within 14 days. Inaction now becomes a problem later — act."
        elif soon:
            dd_note = f"No immediate deadlines. {len(soon)} item(s) due within 60 days. Keep them visible."
        else:
            dd_note = "Calendar is clear in the near term. Review the quarter-end items when they approach."

        return {
            "urgent": urgent,
            "soon": soon,
            "later": later,
            "total_count": len(all_upcoming),
            "daredevil_note": dd_note,
        }

    def add_compliance_item(self, title: str, date: str, notes: str = "", item_type: str = "custom", recurs_annually: bool = False) -> dict[str, Any]:
        item = ComplianceItem(
            item_id=str(uuid.uuid4()),
            title=title,
            date=date,
            item_type=item_type,
            notes=notes,
            recurs_annually=recurs_annually,
        )
        self._store.append_compliance(item)
        return asdict(item)


# ---------------------------------------------------------------------------
# FinancialIntelligenceOrchestrator
# ---------------------------------------------------------------------------

class FinancialIntelligenceOrchestrator:
    """
    Ties all financial agents together.
    Called weekly by the scheduler.
    """

    def __init__(self, store: FinancialStore) -> None:
        self._store = store
        self.fisk = FiskAgent(store)
        self.howard = HowardStarkAgent(store)
        self.daredevil = DaredevilAgent(store)
        self.budget = BudgetTracker(store)

    def weekly_financial_check(self) -> dict[str, Any]:
        """
        Weekly financial intelligence report:
        - Wealth snapshot
        - Passive income payments received
        - Compliance deadlines approaching (next 30 days)
        - Budget status (current month)
        - Fisk's recommended action
        """
        snapshot = self.fisk.get_wealth_snapshot()
        passive = self.howard.get_passive_income_dashboard()
        compliance = self.daredevil.get_upcoming_deadlines(days=30)
        budget_status = self.budget.get_monthly_budget_status()

        # Fisk's top action from health assessment
        health = self.fisk.assess_financial_health()
        top_action = health["actions"][0] if health["actions"] else "Maintain current position."

        return {
            "generated_at": _now_iso(),
            "week": _today(),
            "net_worth": snapshot["net_worth"],
            "monthly_cashflow": snapshot["monthly_cashflow"],
            "passive_income_monthly": snapshot["passive_income_monthly"],
            "fisk_assessment": snapshot["fisk_assessment"],
            "passive_income": {
                "total_monthly": passive["total_monthly"],
                "needs_attention": passive["needs_attention"],
                "growth_trend": passive["growth_trend"],
                "howard_note": passive["howard_note"],
            },
            "compliance_next_30_days": compliance,
            "budget_status": {
                "month": budget_status["month"],
                "total_spent": budget_status["total_spent"],
                "total_budget": budget_status["total_budget"],
                "percent_used": budget_status["percent_used"],
            },
            "health_score": health["score"],
            "fisk_recommended_action": top_action,
        }

    def get_dashboard_status(self) -> dict[str, Any]:
        """For Already Working zone."""
        try:
            snapshot = self.fisk.get_wealth_snapshot()
            passive = self.howard.get_passive_income_dashboard()
            stale = self.howard.flag_stale_streams()
            upcoming = self.daredevil.get_upcoming_deadlines(days=30)

            return {
                "ok": True,
                "net_worth": snapshot["net_worth"],
                "passive_income_monthly": snapshot["passive_income_monthly"],
                "monthly_cashflow": snapshot["monthly_cashflow"],
                "stale_streams": len(stale),
                "compliance_items_30d": len(upcoming),
                "last_updated": snapshot["last_updated"],
            }
        except Exception as exc:
            logger.debug("FinancialIntelligenceOrchestrator.get_dashboard_status error: %s", exc)
            return {"ok": False, "error": str(exc)}

    def get_briefing_item(self) -> dict[str, Any] | None:
        """
        If there's something financially important to surface today, return a briefing item.
        Returns None if nothing to surface.
        """
        try:
            # Check compliance deadline in 7 days
            urgent = self.daredevil.get_upcoming_deadlines(days=7)
            if urgent:
                d = urgent[0]
                return {
                    "text": f"Compliance deadline in {d['days_until']} day(s): {d['title']}",
                    "sub": [d.get("notes", "")],
                    "priority": "high",
                    "agent": "Daredevil",
                    "timestamp": _now_iso(),
                }

            # Check stale passive income streams
            stale = self.howard.flag_stale_streams()
            if stale:
                names = ", ".join(s.name for s in stale[:3])
                return {
                    "text": f"Passive income check: {len(stale)} stream(s) haven't paid in {HowardStarkAgent.STALE_DAYS}+ days — {names}",
                    "sub": [f"Last payment: {s.last_payment_date or 'never'}" for s in stale[:3]],
                    "priority": "normal",
                    "agent": "Howard Stark",
                    "timestamp": _now_iso(),
                }

            # Check negative cashflow
            snapshot = self.fisk.get_wealth_snapshot()
            if snapshot["monthly_cashflow"] < -100:
                return {
                    "text": f"Cashflow alert: spending exceeds income by ${abs(snapshot['monthly_cashflow']):,.0f} this month.",
                    "sub": [snapshot["fisk_assessment"]],
                    "priority": "high",
                    "agent": "Fisk",
                    "timestamp": _now_iso(),
                }

        except Exception as exc:
            logger.debug("get_briefing_item error: %s", exc)

        return None


# ---------------------------------------------------------------------------
# Seed data
# ---------------------------------------------------------------------------

def _seed_if_empty(store: FinancialStore) -> None:
    """Seed with sample accounts, passive income streams if store is empty."""

    # Accounts
    if not store.load_accounts():
        store.save_accounts([
            Account(
                account_id="chase-checking",
                name="Chase Checking",
                account_type="checking",
                institution="Chase",
                balance=4800.0,
                currency="USD",
                last_updated=_today(),
                notes="Primary household checking account.",
                is_manual=True,
                hidden=False,
            ),
            Account(
                account_id="fidelity-brokerage",
                name="Fidelity Brokerage",
                account_type="investment",
                institution="Fidelity",
                balance=24500.0,
                currency="USD",
                last_updated=_today(),
                notes="Long-term investment account.",
                is_manual=True,
                hidden=False,
            ),
            Account(
                account_id="high-yield-savings",
                name="High-Yield Savings",
                account_type="savings",
                institution="Marcus by Goldman Sachs",
                balance=12000.0,
                currency="USD",
                last_updated=_today(),
                notes="Emergency fund + short-term reserves.",
                is_manual=True,
                hidden=False,
            ),
        ])
        logger.info("FinancialStore: seeded 3 sample accounts")

    # Passive income streams
    if not store.load_streams():
        store.save_streams([
            PassiveIncomeStream(
                stream_id="book-royalty-main",
                name="Book Royalties",
                stream_type="book_royalty",
                monthly_average=320.0,
                last_payment=312.50,
                last_payment_date=_today(),
                ytd_total=320.0,
                active=True,
                platform="KDP / IngramSpark",
                tracking_url="",
                notes="Primary book royalty stream. Paid monthly.",
                growth_rate=2.5,
            ),
            PassiveIncomeStream(
                stream_id="course-revenue-main",
                name="Online Course Revenue",
                stream_type="course_revenue",
                monthly_average=210.0,
                last_payment=198.00,
                last_payment_date=_today(),
                ytd_total=210.0,
                active=True,
                platform="Teachable",
                tracking_url="",
                notes="Passive income from online courses. Monthly payout.",
                growth_rate=4.0,
            ),
        ])
        logger.info("FinancialStore: seeded 2 sample passive income streams")


# ---------------------------------------------------------------------------
# Module-level singleton
# ---------------------------------------------------------------------------

_finance_singleton: FinancialIntelligenceOrchestrator | None = None


def init_finance(runtime: Any = None) -> FinancialIntelligenceOrchestrator:
    """
    Create and return the module-level FinancialIntelligenceOrchestrator singleton.
    Safe to call multiple times — subsequent calls return the existing instance.
    """
    global _finance_singleton

    if _finance_singleton is not None:
        return _finance_singleton

    store = FinancialStore()
    _seed_if_empty(store)
    orchestrator = FinancialIntelligenceOrchestrator(store)
    _finance_singleton = orchestrator
    logger.info("FinancialIntelligenceOrchestrator singleton initialised")
    return orchestrator


def get_finance() -> FinancialIntelligenceOrchestrator | None:
    return _finance_singleton
