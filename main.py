"""
Business Profit Calculator (Naira Version)
Tracks capital, sales, expenses, returns, credit sales and business progress.
"""

import json
import os
import uuid
from datetime import datetime
from dataclasses import dataclass, asdict
from enum import Enum
from typing import Dict, List, Optional


# ==================== ENUMS ====================

class TransactionType(Enum):
    CAPITAL = "capital"
    SALE = "sale"
    CREDIT_SALE = "credit_sale"
    CREDIT_PAYMENT = "credit_payment"
    EXPENSE = "expense"
    RETURN = "return"


class PaymentStatus(Enum):
    PAID = "paid"
    UNPAID = "unpaid"
    PARTIAL = "partial"


# ==================== DATA MODELS ====================

@dataclass
class Product:
    id: str
    name: str
    purchase_price: float
    selling_price: float
    quantity: int
    unit: str = "pcs"

    def to_dict(self):
        return asdict(self)

    @classmethod
    def from_dict(cls, data):
        return cls(**data)


@dataclass
class Transaction:
    id: str
    type: TransactionType
    amount: float
    description: str
    date: str
    product_id: Optional[str] = None
    quantity: int = 0
    payment_status: PaymentStatus = PaymentStatus.PAID
    related_id: Optional[str] = None

    def to_dict(self):
        data = asdict(self)
        data["type"] = self.type.value
        data["payment_status"] = self.payment_status.value
        return data

    @classmethod
    def from_dict(cls, data):
        data["type"] = TransactionType(data["type"])
        data["payment_status"] = PaymentStatus(data["payment_status"])
        return cls(**data)


# ==================== BUSINESS MANAGER ====================

class BusinessManager:
    def __init__(self, filename: str = "business_data.json"):
        self.filename = filename
        self.capital = 0.0
        self.products: Dict[str, Product] = {}
        self.transactions: List[Transaction] = []
        self.load()

    def load(self):
        if not os.path.exists(self.filename):
            return
        try:
            with open(self.filename, "r") as f:
                data = json.load(f)
            self.capital = data.get("capital", 0.0)
            self.products = {
                pid: Product.from_dict(p)
                for pid, p in data.get("products", {}).items()
            }
            self.transactions = [
                Transaction.from_dict(t) for t in data.get("transactions", [])
            ]
            print(f"✓ Loaded {len(self.products)} products and {len(self.transactions)} transactions")
        except Exception as e:
            print(f"⚠ Error loading data: {e}. Starting fresh.")

    def save(self):
        data = {
            "capital": self.capital,
            "products": {pid: p.to_dict() for pid, p in self.products.items()},
            "transactions": [t.to_dict() for t in self.transactions],
        }
        with open(self.filename, "w") as f:
            json.dump(data, f, indent=2)
        print("✓ Data saved")

    def set_capital(self, amount: float):
        if amount <= 0:
            raise ValueError("Capital must be greater than 0")
        self.capital = amount
        t = Transaction(
            id=str(uuid.uuid4()),
            type=TransactionType.CAPITAL,
            amount=amount,
            description="Initial / Updated Capital",
            date=datetime.now().isoformat(),
        )
        self.transactions.append(t)
        self.save()
        print(f"✓ Capital set to ₦{amount:,.2f}")

    def add_product(self, name: str, purchase_price: float, selling_price: float, qty: int, unit: str = "pcs"):
        if purchase_price < 0 or selling_price < 0 or qty < 0:
            raise ValueError("Prices and quantity cannot be negative")
        pid = str(uuid.uuid4())
        product = Product(pid, name, purchase_price, selling_price, qty, unit)
        self.products[pid] = product

        # Record the cost of buying the goods as an expense
        cost = purchase_price * qty
        t = Transaction(
            id=str(uuid.uuid4()),
            type=TransactionType.EXPENSE,
            amount=cost,
            description=f"Bought {qty} {unit} of {name}",
            date=datetime.now().isoformat(),
            product_id=pid,
            quantity=qty,
        )
        self.transactions.append(t)
        self.save()
        print(f"✓ Product added: {name} ({qty} {unit})")
        return pid

    def record_sale(self, product_id: str, qty: int, is_credit: bool = False):
        if product_id not in self.products:
            raise ValueError("Product not found")
        product = self.products[product_id]
        if product.quantity < qty:
            raise ValueError(f"Not enough stock. Available: {product.quantity}")

        product.quantity -= qty
        amount = product.selling_price * qty

        t_type = TransactionType.CREDIT_SALE if is_credit else TransactionType.SALE
        status = PaymentStatus.UNPAID if is_credit else PaymentStatus.PAID

        t = Transaction(
            id=str(uuid.uuid4()),
            type=t_type,
            amount=amount,
            description=f"Sold {qty} {product.unit} of {product.name}",
            date=datetime.now().isoformat(),
            product_id=product_id,
            quantity=qty,
            payment_status=status,
        )
        self.transactions.append(t)
        self.save()

        kind = "on CREDIT" if is_credit else "CASH"
        print(f"✓ Sale recorded ({kind}): ₦{amount:,.2f}")
        return t.id

    def record_expense(self, amount: float, description: str):
        if amount <= 0:
            raise ValueError("Expense must be positive")
        t = Transaction(
            id=str(uuid.uuid4()),
            type=TransactionType.EXPENSE,
            amount=amount,
            description=description,
            date=datetime.now().isoformat(),
        )
        self.transactions.append(t)
        self.save()
        print(f"✓ Expense recorded: ₦{amount:,.2f}")
        return t.id

    def record_return(self, sale_id: str, qty: Optional[int] = None):
        sale = next((t for t in self.transactions if t.id == sale_id and t.type in (
            TransactionType.SALE, TransactionType.CREDIT_SALE)), None)
        if not sale:
            raise ValueError("Sale transaction not found")

        if qty is None:
            qty = sale.quantity
        if qty > sale.quantity:
            raise ValueError("Cannot return more than was sold")

        product = self.products.get(sale.product_id)
        if product:
            product.quantity += qty
            return_amount = product.selling_price * qty
        else:
            return_amount = (sale.amount / sale.quantity) * qty

        t = Transaction(
            id=str(uuid.uuid4()),
            type=TransactionType.RETURN,
            amount=return_amount,
            description=f"Return of {qty} items from sale {sale_id[:8]}",
            date=datetime.now().isoformat(),
            product_id=sale.product_id,
            quantity=qty,
            related_id=sale_id,
        )
        self.transactions.append(t)
        self.save()
        print(f"✓ Return recorded: ₦{return_amount:,.2f}")
        return t.id

    def record_credit_payment(self, credit_sale_id: str, amount: float):
        sale = next((t for t in self.transactions
                     if t.id == credit_sale_id and t.type == TransactionType.CREDIT_SALE), None)
        if not sale:
            raise ValueError("Credit sale not found")

        already_paid = sum(
            t.amount for t in self.transactions
            if t.related_id == credit_sale_id and t.type == TransactionType.CREDIT_PAYMENT
        )
        remaining = sale.amount - already_paid

        if amount > remaining + 0.01:
            raise ValueError(f"Payment exceeds remaining balance (₦{remaining:,.2f})")

        t = Transaction(
            id=str(uuid.uuid4()),
            type=TransactionType.CREDIT_PAYMENT,
            amount=amount,
            description=f"Payment for credit sale {credit_sale_id[:8]}",
            date=datetime.now().isoformat(),
            related_id=credit_sale_id,
        )
        self.transactions.append(t)

        if abs(amount - remaining) < 0.01:
            sale.payment_status = PaymentStatus.PAID
        else:
            sale.payment_status = PaymentStatus.PARTIAL

        self.save()
        print(f"✓ Credit payment recorded: ₦{amount:,.2f}")
        return t.id

    def get_metrics(self):
        sales = 0.0
        credit_sales = 0.0
        credit_payments = 0.0
        expenses = 0.0
        returns = 0.0
        cogs = 0.0

        for t in self.transactions:
            if t.type == TransactionType.SALE:
                sales += t.amount
                if t.product_id and t.product_id in self.products:
                    cogs += self.products[t.product_id].purchase_price * t.quantity
            elif t.type == TransactionType.CREDIT_SALE:
                credit_sales += t.amount
                if t.product_id and t.product_id in self.products:
                    cogs += self.products[t.product_id].purchase_price * t.quantity
            elif t.type == TransactionType.CREDIT_PAYMENT:
                credit_payments += t.amount
            elif t.type == TransactionType.EXPENSE:
                expenses += t.amount
            elif t.type == TransactionType.RETURN:
                returns += t.amount

        net_sales = sales + credit_payments - returns
        gross_profit = (sales + credit_sales - returns) - cogs
        net_profit = net_sales - expenses
        balance = self.capital + net_profit
        outstanding = credit_sales - credit_payments
        margin = (net_profit / net_sales * 100) if net_sales > 0 else 0.0

        return {
            "capital": self.capital,
            "total_sales": sales,
            "credit_sales": credit_sales,
            "credit_payments": credit_payments,
            "expenses": expenses,
            "returns": returns,
            "cogs": cogs,
            "gross_profit": gross_profit,
            "net_profit": net_profit,
            "current_balance": balance,
            "outstanding_credits": outstanding,
            "profit_margin": margin,
        }

    def progress_report(self):
        m = self.get_metrics()
        print("\n" + "=" * 55)
        print("           BUSINESS PROGRESS REPORT")
        print("=" * 55)
        print(f"Capital Invested      : ₦{m['capital']:,.2f}")
        print(f"Cash Sales            : ₦{m['total_sales']:,.2f}")
        print(f"Credit Sales          : ₦{m['credit_sales']:,.2f}")
        print(f"Credit Payments       : ₦{m['credit_payments']:,.2f}")
        print(f"Goods Returns         : ₦{m['returns']:,.2f}")
        print(f"Total Expenses        : ₦{m['expenses']:,.2f}")
        print(f"Cost of Goods Sold    : ₦{m['cogs']:,.2f}")
        print("-" * 55)
        print(f"Gross Profit          : ₦{m['gross_profit']:,.2f}")
        print(f"Net Profit / Loss     : ₦{m['net_profit']:,.2f}")
        print(f"Current Balance       : ₦{m['current_balance']:,.2f}")
        print(f"Outstanding Credits   : ₦{m['outstanding_credits']:,.2f}")
        print(f"Profit Margin         : {m['profit_margin']:.1f}%")
        print("-" * 55)

        if m["net_profit"] > 0:
            if m["profit_margin"] >= 20:
                status = "EXCELLENT 🚀"
                msg = "Strong profit and healthy margins. Keep it up!"
            elif m["profit_margin"] >= 10:
                status = "GOOD ✅"
                msg = "Business is profitable. Look for ways to improve margins."
            else:
                status = "FAIR ⚠"
                msg = "Making profit but margins are thin. Review costs and prices."
        else:
            status = "LOSS ❌"
            msg = "Business is currently making a loss. Review expenses and sales."

        print(f"Status                : {status}")
        print(f"Comment               : {msg}")
        print("=" * 55)


# ==================== CLI INTERFACE ====================

class App:
    def __init__(self):
        self.bm = BusinessManager()

    def menu(self):
        print("\n" + "=" * 50)
        print("     BUSINESS PROFIT CALCULATOR (₦)")
        print("=" * 50)
        print("1.  Set / Update Capital")
        print("2.  Add Product to Inventory")
        print("3.  Record Cash Sale")
        print("4.  Record Credit Sale")
        print("5.  Record Expense")
        print("6.  Record Goods Return")
        print("7.  Record Credit Payment")
        print("8.  View Inventory")
        print("9.  View Business Metrics")
        print("10. Full Progress Report")
        print("11. Exit")
        print("=" * 50)

    def run(self):
        while True:
            self.menu()
            choice = input("Choose option (1-11): ").strip()

            try:
                if choice == "1":
                    amount = float(input("Enter capital amount (₦): "))
                    self.bm.set_capital(amount)

                elif choice == "2":
                    name = input("Product name: ").strip()
                    pp = float(input("Purchase price (₦): "))
                    sp = float(input("Selling price (₦): "))
                    qty = int(input("Quantity: "))
                    unit = input("Unit (e.g. pcs, kg, packs) [pcs]: ").strip() or "pcs"
                    self.bm.add_product(name, pp, sp, qty, unit)

                elif choice == "3":
                    self._list_products()
                    pid = input("Product ID: ").strip()
                    qty = int(input("Quantity sold: "))
                    self.bm.record_sale(pid, qty, is_credit=False)

                elif choice == "4":
                    self._list_products()
                    pid = input("Product ID: ").strip()
                    qty = int(input("Quantity sold on credit: "))
                    self.bm.record_sale(pid, qty, is_credit=True)

                elif choice == "5":
                    amount = float(input("Expense amount (₦): "))
                    desc = input("Description: ").strip()
                    self.bm.record_expense(amount, desc)

                elif choice == "6":
                    sale_id = input("Original Sale Transaction ID: ").strip()
                    qty_input = input("Quantity to return (leave blank for all): ").strip()
                    qty = int(qty_input) if qty_input else None
                    self.bm.record_return(sale_id, qty)

                elif choice == "7":
                    credit_id = input("Credit Sale Transaction ID: ").strip()
                    amount = float(input("Payment amount (₦): "))
                    self.bm.record_credit_payment(credit_id, amount)

                elif choice == "8":
                    self._show_inventory()

                elif choice == "9":
                    self._show_metrics()

                elif choice == "10":
                    self.bm.progress_report()

                elif choice == "11":
                    print("\nThank you for using Business Profit Calculator. Goodbye!")
                    break

                else:
                    print("Invalid choice. Please try again.")

            except ValueError as e:
                print(f"❌ Error: {e}")
            except Exception as e:
                print(f"❌ Unexpected error: {e}")

    def _list_products(self):
        if not self.bm.products:
            print("No products yet.")
            return
        print("\nAvailable Products:")
        for p in self.bm.products.values():
            print(f"  ID: {p.id[:8]}... | {p.name} | Stock: {p.quantity} {p.unit} | Sell: ₦{p.selling_price:,.2f}")

    def _show_inventory(self):
        if not self.bm.products:
            print("Inventory is empty.")
            return
        print("\n" + "-" * 75)
        print(f"{'Name':<20} {'Qty':>8} {'Unit':<8} {'Buy (₦)':>12} {'Sell (₦)':>12} {'Value (₦)':>14}")
        print("-" * 75)
        total_value = 0
        for p in self.bm.products.values():
            value = p.quantity * p.purchase_price
            total_value += value
            print(f"{p.name:<20} {p.quantity:>8} {p.unit:<8} {p.purchase_price:>12,.2f} {p.selling_price:>12,.2f} {value:>14,.2f}")
        print("-" * 75)
        print(f"{'Total Inventory Value:':<50} ₦{total_value:,.2f}")

    def _show_metrics(self):
        m = self.bm.get_metrics()
        print("\n" + "=" * 48)
        print("         CURRENT BUSINESS METRICS")
        print("=" * 48)
        print(f"Capital               : ₦{m['capital']:,.2f}")
        print(f"Cash Sales            : ₦{m['total_sales']:,.2f}")
        print(f"Credit Sales          : ₦{m['credit_sales']:,.2f}")
        print(f"Payments Received     : ₦{m['credit_payments']:,.2f}")
        print(f"Returns               : ₦{m['returns']:,.2f}")
        print(f"Expenses              : ₦{m['expenses']:,.2f}")
        print(f"Cost of Goods Sold    : ₦{m['cogs']:,.2f}")
        print("-" * 48)
        print(f"Gross Profit          : ₦{m['gross_profit']:,.2f}")
        print(f"Net Profit / Loss     : ₦{m['net_profit']:,.2f}")
        print(f"Current Balance       : ₦{m['current_balance']:,.2f}")
        print(f"Outstanding Credits   : ₦{m['outstanding_credits']:,.2f}")
        print(f"Profit Margin         : {m['profit_margin']:.1f}%")
        print("=" * 48)


if __name__ == "__main__":
    app = App()
    app.run()
