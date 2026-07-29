"""
Business Profit Calculation Application
A comprehensive system for tracking business finances, inventory, and progress.
"""

import json
import datetime
import os
from typing import List, Dict, Optional, Tuple, Union
from dataclasses import dataclass, asdict
from enum import Enum
import uuid

# ==================== DATA MODELS ====================

class TransactionType(Enum):
    """Types of financial transactions"""
    CAPITAL = "capital"
    SALE = "sale"
    EXPENSE = "expense"
    RETURN = "return"
    CREDIT_SALE = "credit_sale"
    CREDIT_PAYMENT = "credit_payment"
    GOODS_RETURN = "goods_return"

class PaymentStatus(Enum):
    """Payment status for transactions"""
    PAID = "paid"
    UNPAID = "unpaid"
    PARTIAL = "partial"

@dataclass
class Product:
    """Represents a product/item in inventory"""
    id: str
    name: str
    purchase_price: float  # Cost to business
    selling_price: float  # Price to customer
    quantity: int
    unit: str = "pieces"
    
    def to_dict(self) -> Dict:
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'Product':
        return cls(**data)

@dataclass
class Transaction:
    """Represents a financial transaction"""
    id: str
    type: TransactionType
    amount: float
    description: str
    date: str
    product_id: Optional[str] = None
    quantity: int = 0
    payment_status: PaymentStatus = PaymentStatus.PAID
    related_transaction_id: Optional[str] = None  # For returns/credits
    
    def to_dict(self) -> Dict:
        data = asdict(self)
        data['type'] = self.type.value
        data['payment_status'] = self.payment_status.value
        return data
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'Transaction':
        data['type'] = TransactionType(data['type'])
        data['payment_status'] = PaymentStatus(data['payment_status'])
        return cls(**data)

@dataclass
class BusinessMetrics:
    """Calculated business metrics"""
    total_capital: float
    total_sales: float
    total_expenses: float
    total_returns: float
    total_credit_sales: float
    total_credit_payments: float
    net_profit: float
    gross_profit: float
    current_balance: float
    outstanding_credits: float
    profit_margin: float  # Percentage

# ==================== BUSINESS LOGIC ====================

class BusinessFinanceManager:
    """Main class managing all business financial operations"""
    
    def __init__(self, data_file: str = "business_data.json"):
        self.data_file = data_file
        self.products: Dict[str, Product] = {}
        self.transactions: List[Transaction] = []
        self.capital: float = 0.0
        
        self.load_data()
    
    def load_data(self) -> None:
        """Load data from JSON file"""
        if os.path.exists(self.data_file):
            try:
                with open(self.data_file, 'r') as f:
                    data = json.load(f)
                    
                self.capital = data.get('capital', 0.0)
                
                # Load products
                self.products = {
                    pid: Product.from_dict(pdata) 
                    for pid, pdata in data.get('products', {}).items()
                }
                
                # Load transactions
                self.transactions = [
                    Transaction.from_dict(tdata) 
                    for tdata in data.get('transactions', [])
                ]
                
                print(f"Loaded {len(self.products)} products and {len(self.transactions)} transactions")
            except Exception as e:
                print(f"Error loading data: {e}. Starting fresh.")
    
    def save_data(self) -> None:
        """Save data to JSON file"""
        data = {
            'capital': self.capital,
            'products': {pid: p.to_dict() for pid, p in self.products.items()},
            'transactions': [t.to_dict() for t in self.transactions]
        }
        
        try:
            with open(self.data_file, 'w') as f:
                json.dump(data, f, indent=2)
            print("Data saved successfully")
        except Exception as e:
            print(f"Error saving data: {e}")
    
    def set_capital(self, amount: float) -> None:
        """Set initial business capital"""
        if amount <= 0:
            raise ValueError("Capital must be positive")
        
        # Create capital transaction
        transaction = Transaction(
            id=str(uuid.uuid4()),
            type=TransactionType.CAPITAL,
            amount=amount,
            description=f"Initial business capital",
            date=datetime.datetime.now().isoformat()
        )
        
        self.capital = amount
        self.transactions.append(transaction)
        self.save_data()
        print(f"Capital set to ${amount:.2f}")
    
    def add_product(self, name: str, purchase_price: float, 
                   selling_price: float, quantity: int, unit: str = "pieces") -> str:
        """Add a new product to inventory"""
        product_id = str(uuid.uuid4())
        product = Product(
            id=product_id,
            name=name,
            purchase_price=purchase_price,
            selling_price=selling_price,
            quantity=quantity,
            unit=unit
        )
        
        self.products[product_id] = product
        
        # Record expense for purchased goods
        expense_amount = purchase_price * quantity
        expense_transaction = Transaction(
            id=str(uuid.uuid4()),
            type=TransactionType.EXPENSE,
            amount=expense_amount,
            description=f"Purchased {quantity} {unit} of {name}",
            date=datetime.datetime.now().isoformat(),
            product_id=product_id,
            quantity=quantity
        )
        
        self.transactions.append(expense_transaction)
        self.save_data()
        print(f"Added product: {name} (Quantity: {quantity})")
        return product_id
    
    def record_sale(self, product_id: str, quantity: int, 
                   is_credit: bool = False) -> str:
        """Record a sale transaction"""
        if product_id not in self.products:
            raise ValueError(f"Product {product_id} not found")
        
        product = self.products[product_id]
        
        if product.quantity < quantity:
            raise ValueError(f"Insufficient stock. Available: {product.quantity}")
        
        # Update inventory
        product.quantity -= quantity
        
        # Calculate sale amount
        sale_amount = product.selling_price * quantity
        
        # Create transaction
        transaction_type = TransactionType.CREDIT_SALE if is_credit else TransactionType.SALE
        payment_status = PaymentStatus.UNPAID if is_credit else PaymentStatus.PAID
        
        transaction = Transaction(
            id=str(uuid.uuid4()),
            type=transaction_type,
            amount=sale_amount,
            description=f"Sold {quantity} {product.unit} of {product.name}",
            date=datetime.datetime.now().isoformat(),
            product_id=product_id,
            quantity=quantity,
            payment_status=payment_status
        )
        
        self.transactions.append(transaction)
        self.save_data()
        
        status_msg = "on credit" if is_credit else "for cash"
        print(f"Sale recorded: {quantity} {product.unit} of {product.name} {status_msg} - ${sale_amount:.2f}")
        return transaction.id
    
    def record_expense(self, amount: float, description: str) -> str:
        """Record a business expense"""
        if amount <= 0:
            raise ValueError("Expense amount must be positive")
        
        transaction = Transaction(
            id=str(uuid.uuid4()),
            type=TransactionType.EXPENSE,
            amount=amount,
            description=description,
            date=datetime.datetime.now().isoformat()
        )
        
        self.transactions.append(transaction)
        self.save_data()
        print(f"Expense recorded: {description} - ${amount:.2f}")
        return transaction.id
    
    def record_return(self, sale_transaction_id: str, quantity: int = None) -> str:
        """Record a return of goods"""
        # Find the original sale transaction
        original_sale = None
        for t in self.transactions:
            if t.id == sale_transaction_id and t.type in [TransactionType.SALE, TransactionType.CREDIT_SALE]:
                original_sale = t
                break
        
        if not original_sale:
            raise ValueError(f"Sale transaction {sale_transaction_id} not found")
        
        if quantity is None:
            quantity = original_sale.quantity
        
        if quantity > original_sale.quantity:
            raise ValueError(f"Cannot return more than sold. Sold: {original_sale.quantity}")
        
        # Calculate return amount
        product = self.products.get(original_sale.product_id)
        return_amount = (product.selling_price * quantity) if product else (original_sale.amount / original_sale.quantity * quantity)
        
        # Update inventory if product exists
        if product and original_sale.product_id:
            product.quantity += quantity
        
        # Create return transaction
        transaction = Transaction(
            id=str(uuid.uuid4()),
            type=TransactionType.RETURN,
            amount=return_amount,
            description=f"Return of {quantity} items from sale {sale_transaction_id}",
            date=datetime.datetime.now().isoformat(),
            product_id=original_sale.product_id,
            quantity=quantity,
            payment_status=PaymentStatus.PAID,
            related_transaction_id=sale_transaction_id
        )
        
        self.transactions.append(transaction)
        self.save_data()
        print(f"Return recorded: ${return_amount:.2f} for {quantity} items")
        return transaction.id
    
    def record_credit_payment(self, credit_sale_id: str, amount: float) -> str:
        """Record payment for a credit sale"""
        # Find the credit sale
        credit_sale = None
        for t in self.transactions:
            if t.id == credit_sale_id and t.type == TransactionType.CREDIT_SALE:
                credit_sale = t
                break
        
        if not credit_sale:
            raise ValueError(f"Credit sale {credit_sale_id} not found")
        
        # Calculate remaining amount
        paid_amount = sum(
            t.amount for t in self.transactions 
            if t.related_transaction_id == credit_sale_id and t.type == TransactionType.CREDIT_PAYMENT
        )
        
        remaining = credit_sale.amount - paid_amount
        
        if amount > remaining:
            raise ValueError(f"Payment exceeds remaining amount. Remaining: ${remaining:.2f}")
        
        # Create payment transaction
        transaction = Transaction(
            id=str(uuid.uuid4()),
            type=TransactionType.CREDIT_PAYMENT,
            amount=amount,
            description=f"Payment for credit sale {credit_sale_id}",
            date=datetime.datetime.now().isoformat(),
            related_transaction_id=credit_sale_id
        )
        
        # Update payment status
        if amount == remaining:
            credit_sale.payment_status = PaymentStatus.PAID
        else:
            credit_sale.payment_status = PaymentStatus.PARTIAL
        
        self.transactions.append(transaction)
        self.save_data()
        print(f"Credit payment recorded: ${amount:.2f}")
        return transaction.id
    
    def calculate_metrics(self) -> BusinessMetrics:
        """Calculate all business metrics"""
        # Initialize totals
        total_sales = 0.0
        total_expenses = 0.0
        total_returns = 0.0
        total_credit_sales = 0.0
        total_credit_payments = 0.0
        
        # Calculate totals from transactions
        for transaction in self.transactions:
            if transaction.type == TransactionType.SALE:
                total_sales += transaction.amount
            elif transaction.type == TransactionType.EXPENSE:
                total_expenses += transaction.amount
            elif transaction.type == TransactionType.RETURN:
                total_returns += transaction.amount
            elif transaction.type == TransactionType.CREDIT_SALE:
                total_credit_sales += transaction.amount
            elif transaction.type == TransactionType.CREDIT_PAYMENT:
                total_credit_payments += transaction.amount
        
        # Calculate cost of goods sold (COGS)
        cogs = 0.0
        for transaction in self.transactions:
            if transaction.type == TransactionType.SALE and transaction.product_id:
                product = self.products.get(transaction.product_id)
                if product:
                    cogs += product.purchase_price * transaction.quantity
        
        # Calculate gross profit
        gross_profit = total_sales - cogs
        
        # Calculate net profit
        net_profit = (total_sales + total_credit_payments) - (total_expenses + total_returns)
        
        # Calculate current balance
        current_balance = self.capital + net_profit
        
        # Calculate outstanding credits
        outstanding_credits = total_credit_sales - total_credit_payments
        
        # Calculate profit margin
        revenue = total_sales + total_credit_payments
        profit_margin = (net_profit / revenue * 100) if revenue > 0 else 0.0
        
        return BusinessMetrics(
            total_capital=self.capital,
            total_sales=total_sales,
            total_expenses=total_expenses,
            total_returns=total_returns,
            total_credit_sales=total_credit_sales,
            total_credit_payments=total_credit_payments,
            net_profit=net_profit,
            gross_profit=gross_profit,
            current_balance=current_balance,
            outstanding_credits=outstanding_credits,
            profit_margin=profit_margin
        )
    
    def get_inventory_status(self) -> List[Dict]:
        """Get current inventory status"""
        inventory = []
        for product in self.products.values():
            # Calculate total value
            total_value = product.quantity * product.purchase_price
            
            inventory.append({
                'id': product.id,
                'name': product.name,
                'quantity': product.quantity,
                'unit': product.unit,
                'purchase_price': product.purchase_price,
                'selling_price': product.selling_price,
                'total_value': total_value,
                'profit_per_unit': product.selling_price - product.purchase_price
            })
        
        return inventory
    
    def get_transaction_history(self, limit: int = 50) -> List[Transaction]:
        """Get recent transactions"""
        return sorted(self.transactions, key=lambda x: x.date, reverse=True)[:limit]
    
    def generate_progress_report(self) -> Dict:
        """Generate comprehensive business progress report"""
        metrics = self.calculate_metrics()
        inventory = self.get_inventory_status()
        recent_transactions = self.get_transaction_history(10)
        
        # Calculate business health indicators
        liquidity_ratio = metrics.current_balance / (metrics.total_expenses / 30 if metrics.total_expenses > 0 else 1)
        
        # Determine business progress status
        if metrics.net_profit > 0:
            if metrics.profit_margin > 20:
                progress_status = "EXCELLENT"
                progress_message = "Business is highly profitable with strong margins"
            elif metrics.profit_margin > 10:
                progress_status = "GOOD"
                progress_message = "Business is profitable with reasonable margins"
            else:
                progress_status = "FAIR"
                progress_message = "Business is profitable but margins are thin"
        else:
            progress_status = "NEEDS ATTENTION"
            progress_message = "Business is operating at a loss"
        
        report = {
            'report_date': datetime.datetime.now().isoformat(),
            'business_metrics': asdict(metrics),
            'inventory_summary': {
                'total_items': len(inventory),
                'total_inventory_value': sum(item['total_value'] for item in inventory),
                'low_stock_items': [item for item in inventory if item['quantity'] < 10]
            },
            'financial_health': {
                'liquidity_ratio': liquidity_ratio,
                'profit_margin': metrics.profit_margin,
                'outstanding_credits_ratio': (metrics.outstanding_credits / metrics.total_sales * 100) if metrics.total_sales > 0 else 0
            },
            'progress_assessment': {
                'status': progress_status,
                'message': progress_message,
                'recommendations': self._generate_recommendations(metrics, inventory)
            },
            'recent_activity': [t.to_dict() for t in recent_transactions]
        }
        
        return report
    
    def _generate_recommendations(self, metrics: BusinessMetrics, inventory: List[Dict]) -> List[str]:
        """Generate business recommendations based on metrics"""
        recommendations = []
        
        if metrics.outstanding_credits > metrics.total_sales * 0.3:
            recommendations.append("High amount of outstanding credits. Consider stricter credit policies.")
        
        if metrics.profit_margin < 10:
            recommendations.append("Low profit margin. Consider increasing prices or reducing costs.")
        
        low_stock = [item for item in inventory if item['quantity'] < 10]
        if low_stock:
            recommendations.append(f"{len(low_stock)} items are low in stock. Consider restocking.")
        
        if metrics.total_expenses > metrics.total_sales * 0.7:
            recommendations.append("High expense ratio. Review and optimize operational costs.")
        
        if not recommendations:
            recommendations.append("Business is performing well. Continue current operations.")
        
        return recommendations

# ==================== USER INTERFACE ====================

class BusinessAppCLI:
    """Command-line interface for the business application"""
    
    def __init__(self):
        self.manager = BusinessFinanceManager()
        self.running = True
    
    def display_menu(self):
        """Display main menu"""
        print("\n" + "="*50)
        print("BUSINESS PROFIT CALCULATION APPLICATION")
        print("="*50)
        print("1. Set Initial Capital")
        print("2. Add Product to Inventory")
        print("3. Record Sale")
        print("4. Record Expense")
        print("5. Record Return")
        print("6. Record Credit Payment")
        print("7. View Business Metrics")
        print("8. View Inventory")
        print("9. View Transaction History")
        print("10. Generate Progress Report")
        print("11. Save Data")
        print("12. Exit")
        print("="*50)
    
    def run(self):
        """Main application loop"""
        print
