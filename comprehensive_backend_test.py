import requests
import sys
import json
from datetime import datetime

class PizzaShopAPITester:
    def __init__(self, base_url="https://crust-corner.preview.emergentagent.com"):
        self.base_url = base_url
        self.api_url = f"{base_url}/api"
        self.token = None
        self.admin_token = None
        self.tests_run = 0
        self.tests_passed = 0
        self.test_results = []

    def log_test(self, name, success, message="", data=None):
        """Log test results"""
        self.tests_run += 1
        if success:
            self.tests_passed += 1
            print(f"✅ {name}: PASSED - {message}")
        else:
            print(f"❌ {name}: FAILED - {message}")
        
        self.test_results.append({
            'name': name,
            'success': success,
            'message': message,
            'data': data
        })

    def run_test(self, name, method, endpoint, expected_status, data=None, headers=None):
        """Run a single API test"""
        url = f"{self.api_url}/{endpoint}"
        test_headers = {'Content-Type': 'application/json'}
        
        if headers:
            test_headers.update(headers)
        
        if self.admin_token and 'Authorization' not in test_headers:
            test_headers['Authorization'] = f'Bearer {self.admin_token}'

        try:
            if method == 'GET':
                response = requests.get(url, headers=test_headers, timeout=15)
            elif method == 'POST':
                response = requests.post(url, json=data, headers=test_headers, timeout=15)
            elif method == 'PUT':
                response = requests.put(url, json=data, headers=test_headers, timeout=15)
            elif method == 'DELETE':
                response = requests.delete(url, headers=test_headers, timeout=15)

            success = response.status_code == expected_status
            
            if success:
                try:
                    response_data = response.json()
                except:
                    response_data = {}
                self.log_test(name, True, f"Status: {response.status_code}")
                return True, response_data
            else:
                try:
                    error_data = response.json()
                    error_msg = error_data.get('detail', str(error_data))
                except:
                    error_msg = response.text
                self.log_test(name, False, f"Expected {expected_status}, got {response.status_code}. Error: {error_msg}")
                return False, {}

        except Exception as e:
            self.log_test(name, False, f"Error: {str(e)}")
            return False, {}

    def test_init_data(self):
        """Initialize sample data"""
        print("\n🔄 Initializing sample data...")
        success, response = self.run_test(
            "Initialize Data",
            "POST",
            "init-data",
            200
        )
        return success

    def test_admin_login(self):
        """Test admin login with provided credentials"""
        print("\n🔐 Testing Admin Login...")
        success, response = self.run_test(
            "Admin Login",
            "POST",
            "auth/login",
            200,
            data={"email": "admin@pizzashop.com", "password": "admin123"},
            headers={}  # No auth header for login
        )
        
        if success and 'token' in response:
            self.admin_token = response['token']
            admin_user = response.get('user', {})
            if admin_user.get('is_admin'):
                self.log_test("Admin Privileges Check", True, "User has admin privileges")
                return True
            else:
                self.log_test("Admin Privileges Check", False, "User does not have admin privileges")
                return False
        return False

    def test_categories(self):
        """Test categories endpoint"""
        print("\n📂 Testing Categories...")
        success, categories = self.run_test(
            "Get Categories",
            "GET",
            "categories",
            200
        )
        
        if success:
            expected_categories = [
                "Pizza", "Pasta", "Appetizers", "Wings", "Salads", 
                "Burgers", "Hot Subs", "Cold Subs", "Calzone", 
                "Stromboli", "Gyros", "Sides", "Desserts"
            ]
            
            category_names = [cat['name'] for cat in categories]
            missing_categories = [cat for cat in expected_categories if cat not in category_names]
            
            if len(missing_categories) == 0:
                self.log_test("All 13 Categories Present", True, f"Found all {len(categories)} categories")
            else:
                self.log_test("All 13 Categories Present", False, f"Missing: {missing_categories}")
            
            return categories
        return []

    def test_pizza_sizes_accuracy(self):
        """Test pizza sizes - CRITICAL: Should only have Medium, Large, Extra Large (NO Small)"""
        print("\n🍕 Testing Pizza Sizes Accuracy...")
        
        success, products = self.run_test(
            "Get All Products",
            "GET",
            "products",
            200
        )
        
        if not success:
            return False
        
        # Find pizza products
        pizza_products = [p for p in products if 'pizza' in p['name'].lower()]
        
        if not pizza_products:
            self.log_test("Pizza Products Found", False, "No pizza products found")
            return False
        
        self.log_test("Pizza Products Found", True, f"Found {len(pizza_products)} pizza products")
        
        # Check NY Cheese Pizza specifically
        ny_cheese = next((p for p in pizza_products if 'NY Cheese' in p['name']), None)
        
        if ny_cheese:
            sizes = ny_cheese.get('sizes', [])
            size_names = [s['name'] for s in sizes]
            
            # Check for correct sizes
            expected_sizes = ["Medium 12\"", "Large 14\"", "Extra Large 18\""]
            has_small = any('small' in size.lower() for size in size_names)
            has_correct_sizes = all(size in size_names for size in expected_sizes)
            
            if has_small:
                self.log_test("No Small Size Check", False, f"Found Small size in: {size_names}")
            else:
                self.log_test("No Small Size Check", True, "No Small size found - CORRECT")
            
            if has_correct_sizes:
                self.log_test("Correct Pizza Sizes", True, f"NY Cheese has correct sizes: {size_names}")
                
                # Check prices
                medium_price = next((s['price'] for s in sizes if s['name'] == "Medium 12\""), None)
                large_price = next((s['price'] for s in sizes if s['name'] == "Large 14\""), None)
                extra_large_price = next((s['price'] for s in sizes if s['name'] == "Extra Large 18\""), None)
                
                expected_prices = {"Medium 12\"": 16.95, "Large 14\"": 18.95, "Extra Large 18\"": 20.95}
                price_correct = (medium_price == 16.95 and large_price == 18.95 and extra_large_price == 20.95)
                
                if price_correct:
                    self.log_test("NY Cheese Pizza Prices", True, f"Medium: ${medium_price}, Large: ${large_price}, Extra Large: ${extra_large_price}")
                else:
                    self.log_test("NY Cheese Pizza Prices", False, f"Expected: {expected_prices}, Got: Medium: ${medium_price}, Large: ${large_price}, Extra Large: ${extra_large_price}")
            else:
                self.log_test("Correct Pizza Sizes", False, f"Missing expected sizes. Found: {size_names}")
        else:
            self.log_test("NY Cheese Pizza Found", False, "NY Cheese Pizza not found")
        
        return True

    def test_admin_product_crud(self):
        """Test admin product CRUD operations"""
        print("\n⚙️ Testing Admin Product CRUD...")
        
        if not self.admin_token:
            self.log_test("Admin CRUD Test", False, "No admin token available")
            return False
        
        # Get categories first
        success, categories = self.run_test("Get Categories for CRUD", "GET", "categories", 200)
        if not success or not categories:
            return False
        
        pizza_category = next((cat for cat in categories if cat['name'] == 'Pizza'), None)
        if not pizza_category:
            self.log_test("Pizza Category Found", False, "Pizza category not found")
            return False
        
        # Test CREATE product
        test_product = {
            "name": "Test Supreme Pizza",
            "description": "Test pizza with all toppings",
            "category_id": pizza_category['id'],
            "price": 19.95,
            "image_url": "https://example.com/test-pizza.jpg",
            "ingredients": ["Pepperoni", "Sausage", "Mushrooms", "Peppers"],
            "sizes": [
                {"name": "Medium 12\"", "price": 17.95},
                {"name": "Large 14\"", "price": 19.95},
                {"name": "Extra Large 18\"", "price": 21.95}
            ],
            "is_featured": False
        }
        
        success, created_product = self.run_test(
            "Create Product",
            "POST",
            "products",
            200,
            data=test_product
        )
        
        if not success:
            return False
        
        product_id = created_product.get('id')
        if not product_id:
            self.log_test("Product ID Retrieved", False, "No product ID in response")
            return False
        
        # Test READ product
        success, retrieved_product = self.run_test(
            "Get Created Product",
            "GET",
            f"products/{product_id}",
            200
        )
        
        if success:
            if retrieved_product.get('name') == test_product['name']:
                self.log_test("Product Data Integrity", True, "Created product data matches")
            else:
                self.log_test("Product Data Integrity", False, "Product data mismatch")
        
        # Test UPDATE product
        updated_data = {
            **test_product,
            "name": "Updated Test Supreme Pizza",
            "price": 21.95
        }
        
        success, updated_product = self.run_test(
            "Update Product",
            "PUT",
            f"products/{product_id}",
            200,
            data=updated_data
        )
        
        if success and updated_product.get('name') == "Updated Test Supreme Pizza":
            self.log_test("Product Update Verification", True, "Product updated successfully")
        
        # Test SUSPEND product (toggle availability)
        success, suspend_response = self.run_test(
            "Suspend Product",
            "PUT",
            f"products/{product_id}/availability?is_available=false",
            200
        )
        
        # Test DELETE product
        success, delete_response = self.run_test(
            "Delete Product",
            "DELETE",
            f"products/{product_id}",
            200
        )
        
        return True

    def test_customer_registration_and_order(self):
        """Test customer registration and order flow"""
        print("\n👤 Testing Customer Registration and Order Flow...")
        
        # Create test customer
        timestamp = datetime.now().strftime("%H%M%S")
        customer_data = {
            "email": f"testcustomer{timestamp}@example.com",
            "password": "testpass123",
            "full_name": "Test Customer",
            "phone": "(555) 123-4567",
            "address": "123 Test Street, Test City, TS 12345"
        }
        
        success, register_response = self.run_test(
            "Customer Registration",
            "POST",
            "auth/register",
            200,
            data=customer_data,
            headers={}  # No auth for registration
        )
        
        if not success:
            return False
        
        customer_token = register_response.get('token')
        if not customer_token:
            self.log_test("Customer Token Retrieved", False, "No token in registration response")
            return False
        
        # Test customer login
        success, login_response = self.run_test(
            "Customer Login",
            "POST",
            "auth/login",
            200,
            data={"email": customer_data["email"], "password": customer_data["password"]},
            headers={}
        )
        
        # Get products for order
        success, products = self.run_test("Get Products for Order", "GET", "products", 200)
        if not success or not products:
            return False
        
        # Find a pizza product
        pizza_product = next((p for p in products if 'pizza' in p['name'].lower() and p.get('sizes')), None)
        if not pizza_product:
            self.log_test("Pizza Product for Order", False, "No pizza product with sizes found")
            return False
        
        # Create order
        order_data = {
            "items": [
                {
                    "product_id": pizza_product['id'],
                    "quantity": 2,
                    "size": pizza_product['sizes'][0]['name'] if pizza_product.get('sizes') else None,
                    "price": pizza_product['sizes'][0]['price'] if pizza_product.get('sizes') else pizza_product['price']
                }
            ],
            "phone": customer_data["phone"],
            "delivery_address": customer_data["address"],
            "notes": "Test order - please ignore"
        }
        
        success, order_response = self.run_test(
            "Create Customer Order",
            "POST",
            "orders",
            200,
            data=order_data,
            headers={"Authorization": f"Bearer {customer_token}"}
        )
        
        if success:
            order_id = order_response.get('id')
            total_amount = order_response.get('total_amount')
            self.log_test("Order Details", True, f"Order ID: {order_id}, Total: ${total_amount}")
        
        return success

    def test_order_management(self):
        """Test order management by admin"""
        print("\n📋 Testing Order Management...")
        
        if not self.admin_token:
            return False
        
        # Get all orders
        success, orders = self.run_test(
            "Get All Orders (Admin)",
            "GET",
            "orders",
            200
        )
        
        if success and orders:
            order_id = orders[0]['id']
            
            # Test status update
            success, status_response = self.run_test(
                "Update Order Status",
                "PUT",
                f"orders/{order_id}/status?status=confirmed",
                200
            )
            
            return success
        
        return success

    def run_all_tests(self):
        """Run all tests in sequence"""
        print("🚀 Starting Comprehensive Pizza Shop API Tests")
        print("=" * 60)
        
        # Initialize data first
        if not self.test_init_data():
            print("❌ Failed to initialize data - stopping tests")
            return False
        
        # Test admin login
        if not self.test_admin_login():
            print("❌ Admin login failed - stopping admin tests")
            return False
        
        # Test categories
        self.test_categories()
        
        # Test pizza sizes accuracy (CRITICAL)
        self.test_pizza_sizes_accuracy()
        
        # Test admin CRUD operations
        self.test_admin_product_crud()
        
        # Test customer flow
        self.test_customer_registration_and_order()
        
        # Test order management
        self.test_order_management()
        
        # Print summary
        print("\n" + "=" * 60)
        print("📊 TEST SUMMARY")
        print("=" * 60)
        print(f"Total Tests: {self.tests_run}")
        print(f"Passed: {self.tests_passed}")
        print(f"Failed: {self.tests_run - self.tests_passed}")
        print(f"Success Rate: {(self.tests_passed/self.tests_run)*100:.1f}%")
        
        # Print failed tests
        failed_tests = [test for test in self.test_results if not test['success']]
        if failed_tests:
            print("\n❌ FAILED TESTS:")
            for test in failed_tests:
                print(f"  - {test['name']}: {test['message']}")
        
        return self.tests_passed == self.tests_run

def main():
    tester = PizzaShopAPITester()
    success = tester.run_all_tests()
    return 0 if success else 1

if __name__ == "__main__":
    sys.exit(main())