import React, { useState, useEffect, createContext, useContext } from 'react';
import './App.css';
import { BrowserRouter, Routes, Route, Navigate, Link, useLocation } from 'react-router-dom';
import axios from 'axios';
import { Button } from './components/ui/button';
import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from './components/ui/card';
import { Input } from './components/ui/input';
import { Label } from './components/ui/label';
import { Badge } from './components/ui/badge';
import { Tabs, TabsContent, TabsList, TabsTrigger } from './components/ui/tabs';
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from './components/ui/dialog';
import { Textarea } from './components/ui/textarea';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from './components/ui/select';
import { Progress } from './components/ui/progress';
import { toast } from 'sonner';
import { 
  ShoppingCart, 
  User, 
  Pizza, 
  Star, 
  Plus, 
  Minus,
  MapPin,
  Phone,
  Clock,
  Heart,
  Award,
  Utensils,
  Menu,
  X,
  Search,
  Filter,
  ChefHat,
  Truck,
  CreditCard,
  CheckCircle2,
  StarIcon,
  Timer,
  Users,
  TrendingUp,
  Coffee,
  Beef,
  Salad,
  IceCream,
  Sandwich,
  Navigation
} from 'lucide-react';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

// Auth Context
const AuthContext = createContext();

const AuthProvider = ({ children }) => {
  const [user, setUser] = useState(null);
  const [token, setToken] = useState(localStorage.getItem('token'));

  useEffect(() => {
    if (token) {
      axios.defaults.headers.common['Authorization'] = `Bearer ${token}`;
    }
  }, [token]);

  const login = (userData, tokenData) => {
    setUser(userData);
    setToken(tokenData);
    localStorage.setItem('token', tokenData);
    axios.defaults.headers.common['Authorization'] = `Bearer ${tokenData}`;
    toast.success(`Welcome back, ${userData.full_name}!`);
  };

  const logout = () => {
    setUser(null);
    setToken(null);
    localStorage.removeItem('token');
    delete axios.defaults.headers.common['Authorization'];
    toast.success('Logged out successfully');
  };

  return (
    <AuthContext.Provider value={{ user, token, login, logout }}>
      {children}
    </AuthContext.Provider>
  );
};

const useAuth = () => useContext(AuthContext);

// Cart Context
const CartContext = createContext();

const CartProvider = ({ children }) => {
  const [cartItems, setCartItems] = useState([]);
  const [isCartOpen, setIsCartOpen] = useState(false);

  const addToCart = (product, size = null, quantity = 1) => {
    const price = size ? size.price : product.price;
    const itemKey = `${product.id}-${size?.name || 'default'}`;
    
    setCartItems(prev => {
      const existing = prev.find(item => item.key === itemKey);
      if (existing) {
        return prev.map(item => 
          item.key === itemKey 
            ? { ...item, quantity: item.quantity + quantity }
            : item
        );
      }
      return [...prev, {
        key: itemKey,
        product_id: product.id,
        name: product.name,
        price: price,
        quantity,
        size: size?.name || null,
        image_url: product.image_url
      }];
    });
    toast.success(`${product.name} added to cart!`);
  };

  const updateQuantity = (key, quantity) => {
    if (quantity <= 0) {
      removeFromCart(key);
      return;
    }
    setCartItems(prev => 
      prev.map(item => 
        item.key === key ? { ...item, quantity } : item
      )
    );
  };

  const removeFromCart = (key) => {
    setCartItems(prev => prev.filter(item => item.key !== key));
    toast.success('Item removed from cart');
  };

  const clearCart = () => {
    setCartItems([]);
    toast.success('Cart cleared');
  };

  const cartTotal = cartItems.reduce((total, item) => total + (item.price * item.quantity), 0);
  const cartCount = cartItems.reduce((total, item) => total + item.quantity, 0);

  return (
    <CartContext.Provider value={{ 
      cartItems, 
      addToCart, 
      updateQuantity, 
      removeFromCart, 
      clearCart, 
      cartTotal, 
      cartCount,
      isCartOpen,
      setIsCartOpen
    }}>
      {children}
    </CartContext.Provider>
  );
};

const useCart = () => useContext(CartContext);

// Category Icon Mapping
const getCategoryIcon = (categoryName) => {
  const icons = {
    'Pizza': Pizza,
    'Pasta': Utensils,
    'Appetizers': Coffee,
    'Wings': ChefHat,
    'Salads': Salad,
    'Burgers': Beef,
    'Hot Subs': Sandwich,
    'Cold Subs': Sandwich,
    'Calzone': Pizza,
    'Stromboli': Pizza,
    'Gyros': Utensils,
    'Sides': Coffee,
    'Desserts': IceCream
  };
  return icons[categoryName] || Utensils;
};

// Header Component
const Header = () => {
  const { user, logout } = useAuth();
  const { cartCount, setIsCartOpen } = useCart();
  const [isMenuOpen, setIsMenuOpen] = useState(false);
  const location = useLocation();

  const isActive = (path) => location.pathname === path;

  return (
    <header className="bg-white shadow-lg sticky top-0 z-50 border-b border-gray-100">
      <div className="container mx-auto px-4 py-4 flex justify-between items-center">
        <Link to="/" className="flex items-center space-x-3">
          <div className="bg-red-600 p-2 rounded-lg">
            <Pizza className="h-6 w-6 text-white" />
          </div>
          <div>
            <span className="font-bold text-xl text-gray-800">I Love NY Pizza</span>
            <p className="text-xs text-gray-500">Authentic New York Style</p>
          </div>
        </Link>

        {/* Desktop Navigation */}
        <nav className="hidden md:flex space-x-8">
          <Link 
            to="/" 
            className={`font-medium transition-colors flex items-center space-x-1 ${
              isActive('/') ? 'text-red-600' : 'text-gray-600 hover:text-red-600'
            }`}
          >
            <span>Home</span>
          </Link>
          <Link 
            to="/menu" 
            className={`font-medium transition-colors flex items-center space-x-1 ${
              isActive('/menu') ? 'text-red-600' : 'text-gray-600 hover:text-red-600'
            }`}
          >
            <Utensils className="h-4 w-4" />
            <span>Menu</span>
          </Link>
          <Link 
            to="/orders" 
            className={`font-medium transition-colors flex items-center space-x-1 ${
              isActive('/orders') ? 'text-red-600' : 'text-gray-600 hover:text-red-600'
            }`}
          >
            <Timer className="h-4 w-4" />
            <span>Orders</span>
          </Link>
          {user?.is_admin && (
            <Link 
              to="/admin" 
              className={`font-medium transition-colors flex items-center space-x-1 ${
                isActive('/admin') ? 'text-red-600' : 'text-gray-600 hover:text-red-600'
              }`}
            >
              <Users className="h-4 w-4" />
              <span>Admin</span>
            </Link>
          )}
        </nav>

        <div className="flex items-center space-x-4">
          <Button 
            variant="outline" 
            size="sm"
            onClick={() => setIsCartOpen(true)}
            className="relative hover:bg-red-50 hover:border-red-200"
          >
            <ShoppingCart className="h-4 w-4" />
            {cartCount > 0 && (
              <Badge className="absolute -top-2 -right-2 bg-red-600 text-white rounded-full text-xs px-1 animate-pulse">
                {cartCount}
              </Badge>
            )}
          </Button>
          
          {user ? (
            <div className="flex items-center space-x-2">
              <div className="hidden sm:flex flex-col text-right">
                <span className="text-sm font-medium text-gray-700">{user.full_name}</span>
                <span className="text-xs text-gray-500">Welcome back!</span>
              </div>
              <Button variant="outline" size="sm" onClick={logout} className="hover:bg-red-50">
                Logout
              </Button>
            </div>
          ) : (
            <Link to="/auth">
              <Button size="sm" className="bg-red-600 hover:bg-red-700">
                <User className="h-4 w-4 mr-1" />
                Login
              </Button>
            </Link>
          )}

          {/* Mobile Menu Button */}
          <Button 
            variant="ghost" 
            size="sm"
            className="md:hidden"
            onClick={() => setIsMenuOpen(!isMenuOpen)}
          >
            {isMenuOpen ? <X className="h-5 w-5" /> : <Menu className="h-5 w-5" />}
          </Button>
        </div>
      </div>

      {/* Mobile Navigation */}
      {isMenuOpen && (
        <div className="md:hidden border-t bg-white">
          <nav className="container mx-auto px-4 py-4 space-y-3">
            <Link 
              to="/" 
              className={`block font-medium transition-colors ${
                isActive('/') ? 'text-red-600' : 'text-gray-600'
              }`}
              onClick={() => setIsMenuOpen(false)}
            >
              Home
            </Link>
            <Link 
              to="/menu" 
              className={`block font-medium transition-colors ${
                isActive('/menu') ? 'text-red-600' : 'text-gray-600'
              }`}
              onClick={() => setIsMenuOpen(false)}
            >
              Menu
            </Link>
            <Link 
              to="/orders" 
              className={`block font-medium transition-colors ${
                isActive('/orders') ? 'text-red-600' : 'text-gray-600'
              }`}
              onClick={() => setIsMenuOpen(false)}
            >
              Orders
            </Link>
            {user?.is_admin && (
              <Link 
                to="/admin" 
                className={`block font-medium transition-colors ${
                  isActive('/admin') ? 'text-red-600' : 'text-gray-600'
                }`}
                onClick={() => setIsMenuOpen(false)}
              >
                Admin
              </Link>
            )}
          </nav>
        </div>
      )}
    </header>
  );
};

// Mini Cart Component
const MiniCart = () => {
  const { cartItems, updateQuantity, removeFromCart, cartTotal, isCartOpen, setIsCartOpen } = useCart();
  const { user } = useAuth();

  if (!isCartOpen) return null;

  return (
    <div className="fixed inset-0 z-50 overflow-hidden">
      <div className="absolute inset-0 bg-black bg-opacity-50" onClick={() => setIsCartOpen(false)} />
      <div className="absolute right-0 top-0 h-full w-full max-w-md bg-white shadow-xl">
        <div className="flex h-full flex-col">
          <div className="flex items-center justify-between p-4 border-b">
            <h2 className="text-lg font-semibold">Your Order</h2>
            <Button variant="ghost" size="sm" onClick={() => setIsCartOpen(false)}>
              <X className="h-5 w-5" />
            </Button>
          </div>
          
          <div className="flex-1 overflow-y-auto p-4">
            {cartItems.length === 0 ? (
              <div className="text-center py-8">
                <ShoppingCart className="h-12 w-12 mx-auto text-gray-400 mb-4" />
                <p className="text-gray-500">Your cart is empty</p>
              </div>
            ) : (
              <div className="space-y-4">
                {cartItems.map((item) => (
                  <div key={item.key} className="flex items-center space-x-3 bg-gray-50 p-3 rounded-lg">
                    <img
                      src={item.image_url || "https://images.unsplash.com/photo-1565299624946-b28f40a0ae38"}
                      alt={item.name}
                      className="w-12 h-12 object-cover rounded"
                    />
                    <div className="flex-1">
                      <h4 className="font-medium text-sm">{item.name}</h4>
                      {item.size && <p className="text-xs text-gray-600">{item.size}</p>}
                      <p className="text-sm font-bold text-red-600">${item.price}</p>
                    </div>
                    <div className="flex items-center space-x-1">
                      <Button
                        size="sm"
                        variant="outline"
                        onClick={() => updateQuantity(item.key, item.quantity - 1)}
                        className="h-6 w-6 p-0"
                      >
                        <Minus className="h-3 w-3" />
                      </Button>
                      <span className="text-sm w-6 text-center">{item.quantity}</span>
                      <Button
                        size="sm"
                        variant="outline"
                        onClick={() => updateQuantity(item.key, item.quantity + 1)}
                        className="h-6 w-6 p-0"
                      >
                        <Plus className="h-3 w-3" />
                      </Button>
                    </div>
                    <Button
                      size="sm"
                      variant="ghost"
                      onClick={() => removeFromCart(item.key)}
                      className="h-6 w-6 p-0 text-red-500 hover:text-red-700"
                    >
                      <X className="h-3 w-3" />
                    </Button>
                  </div>
                ))}
              </div>
            )}
          </div>
          
          {cartItems.length > 0 && (
            <div className="border-t p-4 space-y-4">
              <div className="flex justify-between text-lg font-bold">
                <span>Total:</span>
                <span className="text-red-600">${cartTotal.toFixed(2)}</span>
              </div>
              {user ? (
                <Link to="/cart" onClick={() => setIsCartOpen(false)}>
                  <Button className="w-full bg-red-600 hover:bg-red-700">
                    Checkout
                  </Button>
                </Link>
              ) : (
                <Link to="/auth" onClick={() => setIsCartOpen(false)}>
                  <Button className="w-full bg-red-600 hover:bg-red-700">
                    Login to Checkout
                  </Button>
                </Link>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

// Home Page
const HomePage = () => {
  const [featuredProducts, setFeaturedProducts] = useState([]);
  const [categories, setCategories] = useState([]);
  const [stats] = useState({
    orders: '1,000+',
    customers: '500+',
    rating: '4.9'
  });
  const { addToCart } = useCart();

  useEffect(() => {
    const fetchData = async () => {
      try {
        const [productsRes, categoriesRes] = await Promise.all([
          axios.get(`${API}/products?featured=true`),
          axios.get(`${API}/categories`)
        ]);
        setFeaturedProducts(productsRes.data);
        setCategories(categoriesRes.data);
      } catch (error) {
        console.error('Error fetching data:', error);
        toast.error('Failed to load menu data');
      }
    };

    fetchData();
  }, []);

  return (
    <div className="min-h-screen">
      {/* Hero Section */}
      <section className="relative bg-gradient-to-br from-red-50 via-orange-50 to-yellow-50 py-20 overflow-hidden">
        <div className="absolute inset-0 bg-white/50" />
        <div className="container mx-auto px-4 relative">
          <div className="grid lg:grid-cols-2 gap-12 items-center">
            <div className="space-y-8">
              <div className="space-y-6">
                <Badge className="bg-red-600 text-white px-4 py-2 text-sm">
                  🔥 15% OFF All Orders Today!
                </Badge>
                <h1 className="text-5xl lg:text-6xl font-bold text-gray-800 leading-tight">
                  Authentic New York
                  <span className="text-red-600 block">Pizza Experience</span>
                </h1>
                <p className="text-xl text-gray-600 leading-relaxed">
                  Handcrafted pizzas made with the finest ingredients, delivering authentic NYC flavors straight to your door. Fresh dough made daily, premium toppings, and recipes passed down through generations.
                </p>
              </div>

              <div className="flex flex-col sm:flex-row gap-4">
                <Link to="/menu">
                  <Button size="lg" className="bg-red-600 hover:bg-red-700 text-white px-8 py-4 text-lg shadow-lg hover:shadow-xl transition-all duration-300 transform hover:-translate-y-1">
                    <Utensils className="mr-2 h-5 w-5" />
                    Order Now
                  </Button>
                </Link>
                <Button variant="outline" size="lg" className="px-8 py-4 text-lg border-2 hover:bg-red-50">
                  <Phone className="mr-2 h-5 w-5" />
                  (470) 545-0095
                </Button>
              </div>

              {/* Stats */}
              <div className="grid grid-cols-3 gap-6 pt-4">
                <div className="text-center">
                  <div className="text-2xl font-bold text-red-600">{stats.orders}</div>
                  <div className="text-sm text-gray-600">Happy Orders</div>
                </div>
                <div className="text-center">
                  <div className="text-2xl font-bold text-red-600">{stats.customers}</div>
                  <div className="text-sm text-gray-600">Customers</div>
                </div>
                <div className="text-center">
                  <div className="flex items-center justify-center">
                    <Star className="h-5 w-5 text-yellow-400 fill-current" />
                    <span className="text-2xl font-bold text-red-600 ml-1">{stats.rating}</span>
                  </div>
                  <div className="text-sm text-gray-600">Rating</div>
                </div>
              </div>

              <div className="flex flex-wrap items-center gap-6 text-sm text-gray-600">
                <div className="flex items-center">
                  <Clock className="h-4 w-4 mr-2 text-red-500" />
                  30-45 min delivery
                </div>
                <div className="flex items-center">
                  <Award className="h-4 w-4 mr-2 text-red-500" />
                  Fresh ingredients
                </div>
                <div className="flex items-center">
                  <Heart className="h-4 w-4 mr-2 text-red-500" />
                  Made with love
                </div>
              </div>
            </div>

            <div className="relative">
              <div className="relative">
                <img
                  src="https://images.unsplash.com/photo-1593504049359-74330189a345"
                  alt="Delicious Pizza"
                  className="rounded-2xl shadow-2xl w-full h-[500px] object-cover transform rotate-1 hover:rotate-0 transition-transform duration-500"
                />
                <div className="absolute -top-4 -left-4 bg-red-600 text-white px-6 py-3 rounded-lg font-bold shadow-lg animate-bounce">
                  15% OFF
                </div>
                <div className="absolute -bottom-4 -right-4 bg-green-600 text-white px-4 py-2 rounded-lg font-medium shadow-lg">
                  <Truck className="h-4 w-4 inline mr-1" />
                  Free Delivery
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* Featured Products */}
      <section className="py-20 bg-white">
        <div className="container mx-auto px-4">
          <div className="text-center mb-16">
            <Badge className="bg-red-100 text-red-600 px-4 py-2 mb-4">
              🌟 Customer Favorites
            </Badge>
            <h2 className="text-4xl lg:text-5xl font-bold text-gray-800 mb-6">Featured Favorites</h2>
            <p className="text-xl text-gray-600 max-w-2xl mx-auto">
              Our most loved pizzas and dishes, crafted with premium ingredients and authentic New York recipes
            </p>
          </div>

          <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-8">
            {featuredProducts.map((product) => (
              <div key={product.id} className="group">
                <Card className="overflow-hidden hover:shadow-2xl transition-all duration-300 transform hover:-translate-y-2 border-0 shadow-lg">
                  <div className="relative h-56 bg-gray-100 overflow-hidden">
                    <img
                      src={product.image_url || "https://images.unsplash.com/photo-1565299624946-b28f40a0ae38"}
                      alt={product.name}
                      className="w-full h-full object-cover group-hover:scale-110 transition-transform duration-500"
                    />
                    <div className="absolute inset-0 bg-gradient-to-t from-black/50 via-transparent to-transparent opacity-0 group-hover:opacity-100 transition-opacity duration-300" />
                    <Badge className="absolute top-4 right-4 bg-red-600 text-white shadow-lg">
                      <Star className="h-3 w-3 mr-1" />
                      Featured
                    </Badge>
                  </div>
                  <CardHeader className="pb-2">
                    <CardTitle className="text-xl font-bold text-gray-800">{product.name}</CardTitle>
                    <CardDescription className="text-gray-600 line-clamp-2">{product.description}</CardDescription>
                  </CardHeader>
                  <CardContent className="pt-2">
                    {product.ingredients && (
                      <div className="flex flex-wrap gap-1 mb-4">
                        {product.ingredients.slice(0, 3).map((ingredient, index) => (
                          <Badge key={index} variant="outline" className="text-xs border-red-200 text-red-600">
                            {ingredient}
                          </Badge>
                        ))}
                        {product.ingredients.length > 3 && (
                          <Badge variant="outline" className="text-xs border-gray-200 text-gray-500">
                            +{product.ingredients.length - 3} more
                          </Badge>
                        )}
                      </div>
                    )}
                  </CardContent>
                  <CardFooter className="flex justify-between items-center pt-0">
                    <div>
                      <span className="text-2xl font-bold text-red-600">${product.price}</span>
                      {product.sizes && product.sizes.length > 0 && (
                        <p className="text-sm text-gray-500">Starting from</p>
                      )}
                    </div>
                    <Button 
                      onClick={() => addToCart(product)} 
                      className="bg-red-600 hover:bg-red-700 shadow-lg hover:shadow-xl transition-all duration-300"
                    >
                      <Plus className="h-4 w-4 mr-1" />
                      Add to Cart
                    </Button>
                  </CardFooter>
                </Card>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Categories Preview */}
      <section className="py-20 bg-gradient-to-br from-gray-50 to-red-50/30">
        <div className="container mx-auto px-4">
          <div className="text-center mb-16">
            <Badge className="bg-orange-100 text-orange-600 px-4 py-2 mb-4">
              🍽️ Full Menu
            </Badge>
            <h2 className="text-4xl lg:text-5xl font-bold text-gray-800 mb-6">Explore Our Menu</h2>
            <p className="text-xl text-gray-600 max-w-2xl mx-auto">
              From classic pizzas to gourmet pasta, fresh salads to indulgent desserts - something delicious for everyone
            </p>
          </div>

          <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 xl:grid-cols-5 gap-6">
            {categories.map((category) => {
              const IconComponent = getCategoryIcon(category.name);
              return (
                <Link key={category.id} to={`/menu?category=${category.id}`}>
                  <Card className="text-center hover:shadow-xl transition-all duration-300 transform hover:-translate-y-2 cursor-pointer group border-0 shadow-md bg-white hover:bg-red-50">
                    <CardContent className="pt-8 pb-6">
                      <div className="h-16 w-16 mx-auto mb-4 bg-gradient-to-br from-red-500 to-red-600 rounded-2xl flex items-center justify-center group-hover:scale-110 transition-transform duration-300 shadow-lg">
                        <IconComponent className="h-8 w-8 text-white" />
                      </div>
                      <h3 className="font-bold text-gray-800 text-lg mb-2">{category.name}</h3>
                      <p className="text-sm text-gray-600 line-clamp-2">{category.description}</p>
                    </CardContent>
                  </Card>
                </Link>
              );
            })}
          </div>
        </div>
      </section>

      {/* Location & Contact */}
      <section className="py-20 bg-white">
        <div className="container mx-auto px-4">
          <div className="grid lg:grid-cols-2 gap-16 items-center">
            <div className="space-y-8">
              <div>
                <Badge className="bg-blue-100 text-blue-600 px-4 py-2 mb-4">
                  📍 Find Us
                </Badge>
                <h2 className="text-4xl lg:text-5xl font-bold text-gray-800 mb-6">Visit Our Location</h2>
                <p className="text-xl text-gray-600 mb-8">
                  Come experience authentic New York pizza in the heart of Woodstock, Georgia. Fresh ingredients, friendly service, and an atmosphere that feels like home.
                </p>
              </div>

              <div className="space-y-6">
                <div className="flex items-start space-x-4 p-4 bg-gray-50 rounded-lg">
                  <div className="bg-red-600 p-3 rounded-lg">
                    <MapPin className="h-6 w-6 text-white" />
                  </div>
                  <div>
                    <h4 className="font-semibold text-gray-800 mb-1">Address</h4>
                    <p className="text-gray-600">10214 HICKORY FLAT HWY, Woodstock, GA 30188</p>
                  </div>
                </div>

                <div className="flex items-start space-x-4 p-4 bg-gray-50 rounded-lg">
                  <div className="bg-green-600 p-3 rounded-lg">
                    <Phone className="h-6 w-6 text-white" />
                  </div>
                  <div>
                    <h4 className="font-semibold text-gray-800 mb-1">Phone</h4>
                    <p className="text-gray-600">(470) 545-0095</p>
                  </div>
                </div>

                <div className="flex items-start space-x-4 p-4 bg-gray-50 rounded-lg">
                  <div className="bg-blue-600 p-3 rounded-lg">
                    <Clock className="h-6 w-6 text-white" />
                  </div>
                  <div>
                    <h4 className="font-semibold text-gray-800 mb-1">Hours</h4>
                    <p className="text-gray-600">Monday - Sunday: 11:00 AM - 10:00 PM</p>
                  </div>
                </div>
              </div>
            </div>

            <div className="relative">
              <img
                src="https://images.unsplash.com/photo-1542239367-2a258bfc0f3b"
                alt="Restaurant Interior"
                className="rounded-2xl shadow-2xl w-full h-[400px] object-cover"
              />
              <div className="absolute inset-0 bg-gradient-to-t from-black/30 via-transparent to-transparent rounded-2xl" />
              <div className="absolute bottom-6 left-6 text-white">
                <h4 className="text-xl font-bold mb-2">Cozy Atmosphere</h4>
                <p className="text-white/90">Perfect for family dinners and casual dining</p>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* Mini Cart */}
      <MiniCart />
    </div>
  );
};

// Enhanced Menu Page with Search and Filters
const MenuPage = () => {
  const [products, setProducts] = useState([]);
  const [categories, setCategories] = useState([]);
  const [selectedCategory, setSelectedCategory] = useState('all');
  const [selectedProduct, setSelectedProduct] = useState(null);
  const [selectedSize, setSelectedSize] = useState(null);
  const [searchTerm, setSearchTerm] = useState('');
  const [isLoading, setIsLoading] = useState(true);
  const { addToCart } = useCart();

  useEffect(() => {
    const fetchData = async () => {
      try {
        setIsLoading(true);
        const [productsRes, categoriesRes] = await Promise.all([
          axios.get(`${API}/products`),
          axios.get(`${API}/categories`)
        ]);
        setProducts(productsRes.data);
        setCategories(categoriesRes.data);
      } catch (error) {
        console.error('Error fetching data:', error);
        toast.error('Failed to load menu data');
      } finally {
        setIsLoading(false);
      }
    };

    fetchData();
  }, []);

  const filteredProducts = products.filter(product => {
    const matchesCategory = selectedCategory === 'all' || product.category_id === selectedCategory;
    const matchesSearch = product.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
                         product.description?.toLowerCase().includes(searchTerm.toLowerCase());
    return matchesCategory && matchesSearch;
  });

  const handleAddToCart = () => {
    if (selectedProduct) {
      addToCart(selectedProduct, selectedSize);
      setSelectedProduct(null);
      setSelectedSize(null);
    }
  };

  if (isLoading) {
    return (
      <div className="container mx-auto px-4 py-16">
        <div className="text-center">
          <div className="animate-spin rounded-full h-16 w-16 border-b-2 border-red-600 mx-auto mb-4"></div>
          <p className="text-gray-600">Loading delicious menu...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="container mx-auto px-4 py-8">
      {/* Header */}
      <div className="text-center mb-12">
        <Badge className="bg-red-100 text-red-600 px-4 py-2 mb-4">
          🍕 Our Complete Menu
        </Badge>
        <h1 className="text-4xl lg:text-5xl font-bold text-gray-800 mb-4">Delicious Food Menu</h1>
        <p className="text-xl text-gray-600 max-w-2xl mx-auto">
          Fresh ingredients, authentic flavors, and recipes crafted with passion
        </p>
      </div>

      {/* Search Bar */}
      <div className="max-w-md mx-auto mb-8">
        <div className="relative">
          <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400 h-5 w-5" />
          <Input
            type="text"
            placeholder="Search for food..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="pl-10 pr-4 py-3 border-2 border-gray-200 focus:border-red-500 rounded-xl"
          />
        </div>
      </div>

      {/* Category Filter */}
      <div className="mb-12">
        <div className="flex items-center justify-center mb-6">
          <Filter className="h-5 w-5 text-gray-500 mr-2" />
          <span className="text-lg font-medium text-gray-700">Filter by Category</span>
        </div>
        <div className="flex flex-wrap justify-center gap-3">
          <Button
            variant={selectedCategory === 'all' ? 'default' : 'outline'}
            onClick={() => setSelectedCategory('all')}
            className={`transition-all duration-300 ${
              selectedCategory === 'all' 
                ? 'bg-red-600 hover:bg-red-700 shadow-lg' 
                : 'hover:bg-red-50 hover:border-red-200'
            }`}
          >
            All Items ({products.length})
          </Button>
          {categories.map((category) => {
            const categoryProducts = products.filter(p => p.category_id === category.id);
            const IconComponent = getCategoryIcon(category.name);
            return (
              <Button
                key={category.id}
                variant={selectedCategory === category.id ? 'default' : 'outline'}
                onClick={() => setSelectedCategory(category.id)}
                className={`transition-all duration-300 ${
                  selectedCategory === category.id 
                    ? 'bg-red-600 hover:bg-red-700 shadow-lg' 
                    : 'hover:bg-red-50 hover:border-red-200'
                }`}
              >
                <IconComponent className="h-4 w-4 mr-2" />
                {category.name} ({categoryProducts.length})
              </Button>
            );
          })}
        </div>
      </div>

      {/* Products Grid */}
      {filteredProducts.length === 0 ? (
        <div className="text-center py-16">
          <Search className="h-16 w-16 text-gray-300 mx-auto mb-4" />
          <h3 className="text-xl font-medium text-gray-600 mb-2">No items found</h3>
          <p className="text-gray-500">Try adjusting your search or category filter</p>
        </div>
      ) : (
        <div className="grid sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-8">
          {filteredProducts.map((product) => (
            <div key={product.id} className="group">
              <Card className="overflow-hidden hover:shadow-2xl transition-all duration-300 transform hover:-translate-y-2 border-0 shadow-lg h-full">
                <div className="relative h-48 bg-gray-100 overflow-hidden">
                  <img
                    src={product.image_url || "https://images.unsplash.com/photo-1565299624946-b28f40a0ae38"}
                    alt={product.name}
                    className="w-full h-full object-cover group-hover:scale-110 transition-transform duration-500"
                  />
                  <div className="absolute inset-0 bg-gradient-to-t from-black/50 via-transparent to-transparent opacity-0 group-hover:opacity-100 transition-opacity duration-300" />
                  {product.is_featured && (
                    <Badge className="absolute top-3 right-3 bg-red-600 text-white shadow-lg">
                      <Star className="h-3 w-3 mr-1" />
                      Featured
                    </Badge>
                  )}
                </div>
                
                <CardHeader className="pb-2">
                  <CardTitle className="text-lg font-bold text-gray-800 line-clamp-2">{product.name}</CardTitle>
                  <CardDescription className="text-gray-600 text-sm line-clamp-2">{product.description}</CardDescription>
                </CardHeader>
                
                <CardContent className="pt-2 flex-1">
                  {product.ingredients && product.ingredients.length > 0 && (
                    <div className="flex flex-wrap gap-1 mb-4">
                      {product.ingredients.slice(0, 2).map((ingredient, index) => (
                        <Badge key={index} variant="outline" className="text-xs border-red-200 text-red-600">
                          {ingredient}
                        </Badge>
                      ))}
                      {product.ingredients.length > 2 && (
                        <Badge variant="outline" className="text-xs border-gray-200 text-gray-500">
                          +{product.ingredients.length - 2}
                        </Badge>
                      )}
                    </div>
                  )}
                </CardContent>
                
                <CardFooter className="flex justify-between items-center pt-0">
                  <div>
                    <span className="text-xl font-bold text-red-600">${product.price}</span>
                    {product.sizes && product.sizes.length > 0 && (
                      <p className="text-xs text-gray-500">Multiple sizes</p>
                    )}
                  </div>
                  <Button 
                    onClick={() => {
                      setSelectedProduct(product);
                      if (product.sizes && product.sizes.length > 0) {
                        setSelectedSize(product.sizes[product.sizes.length - 1]);
                      }
                    }}
                    className="bg-red-600 hover:bg-red-700 shadow-lg hover:shadow-xl transition-all duration-300"
                  >
                    <Plus className="h-4 w-4 mr-1" />
                    Add
                  </Button>
                </CardFooter>
              </Card>
            </div>
          ))}
        </div>
      )}

      {/* Product Detail Modal */}
      <Dialog open={!!selectedProduct} onOpenChange={(open) => !open && setSelectedProduct(null)}>
        <DialogContent className="max-w-md z-50">
          {selectedProduct && (
            <>
              <DialogHeader>
                <DialogTitle className="text-xl font-bold">{selectedProduct.name}</DialogTitle>
                <DialogDescription className="text-gray-600">{selectedProduct.description}</DialogDescription>
              </DialogHeader>
              
              <div className="space-y-4">
                <img
                  src={selectedProduct.image_url || "https://images.unsplash.com/photo-1565299624946-b28f40a0ae38"}
                  alt={selectedProduct.name}
                  className="w-full h-48 object-cover rounded-lg"
                />

                {selectedProduct.ingredients && (
                  <div>
                    <Label className="font-medium">Ingredients</Label>
                    <div className="flex flex-wrap gap-1 mt-2">
                      {selectedProduct.ingredients.map((ingredient, index) => (
                        <Badge key={index} variant="outline" className="text-xs">
                          {ingredient}
                        </Badge>
                      ))}
                    </div>
                  </div>
                )}

                {selectedProduct.sizes && selectedProduct.sizes.length > 0 && (
                  <div>
                    <Label className="font-medium mb-2 block">Choose Size</Label>
                    <Select 
                      value={selectedSize?.name} 
                      onValueChange={(sizeName) => {
                        const size = selectedProduct.sizes.find(s => s.name === sizeName);
                        setSelectedSize(size);
                      }}
                    >
                      <SelectTrigger className="border-2 border-gray-200 focus:border-red-500">
                        <SelectValue placeholder="Select size" />
                      </SelectTrigger>
                      <SelectContent>
                        {selectedProduct.sizes.map((size) => (
                          <SelectItem key={size.name} value={size.name}>
                            <div className="flex justify-between items-center w-full">
                              <span>{size.name}</span>
                              <span className="font-bold text-red-600 ml-4">${size.price}</span>
                            </div>
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  </div>
                )}

                <div className="text-center py-4">
                  <span className="text-3xl font-bold text-red-600">
                    ${selectedSize ? selectedSize.price : selectedProduct.price}
                  </span>
                </div>
              </div>

              <DialogFooter>
                <Button onClick={handleAddToCart} className="bg-red-600 hover:bg-red-700 w-full">
                  <ShoppingCart className="h-4 w-4 mr-2" />
                  Add to Cart
                </Button>
              </DialogFooter>
            </>
          )}
        </DialogContent>
      </Dialog>

      <MiniCart />
    </div>
  );
};

// Enhanced Auth Page
const AuthPage = () => {
  const [isLogin, setIsLogin] = useState(true);
  const [formData, setFormData] = useState({
    email: '',
    password: '',
    full_name: '',
    phone: '',
    address: ''
  });
  const [isLoading, setIsLoading] = useState(false);
  const { login } = useAuth();

  const handleSubmit = async (e) => {
    e.preventDefault();
    setIsLoading(true);
    
    try {
      const endpoint = isLogin ? '/auth/login' : '/auth/register';
      const response = await axios.post(`${API}${endpoint}`, formData);
      
      login(response.data.user, response.data.token);
      
      // Reset form
      setFormData({
        email: '',
        password: '',
        full_name: '',
        phone: '',
        address: ''
      });
      
      // Redirect to menu or previous page
      window.location.href = '/menu';
      
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Something went wrong');
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-red-50 via-orange-50 to-yellow-50 py-16">
      <div className="container mx-auto px-4">
        <div className="max-w-md mx-auto">
          <Card className="shadow-2xl border-0">
            <CardHeader className="text-center pb-8">
              <div className="bg-red-600 p-4 rounded-full w-16 h-16 mx-auto mb-4">
                <User className="h-8 w-8 text-white" />
              </div>
              <CardTitle className="text-2xl font-bold text-gray-800">
                {isLogin ? 'Welcome Back!' : 'Join Our Family'}
              </CardTitle>
              <CardDescription className="text-gray-600">
                {isLogin ? 'Sign in to your account to continue ordering' : 'Create your account and start enjoying authentic NYC pizza'}
              </CardDescription>
            </CardHeader>
            
            <CardContent className="pb-8">
              <form onSubmit={handleSubmit} className="space-y-6">
                <div>
                  <Label htmlFor="email" className="font-medium">Email Address</Label>
                  <Input
                    id="email"
                    type="email"
                    value={formData.email}
                    onChange={(e) => setFormData({...formData, email: e.target.value})}
                    required
                    className="mt-2 border-2 border-gray-200 focus:border-red-500 transition-colors"
                    placeholder="your@email.com"
                  />
                </div>
                
                <div>
                  <Label htmlFor="password" className="font-medium">Password</Label>
                  <Input
                    id="password"
                    type="password"
                    value={formData.password}
                    onChange={(e) => setFormData({...formData, password: e.target.value})}
                    required
                    className="mt-2 border-2 border-gray-200 focus:border-red-500 transition-colors"
                    placeholder="Enter your password"
                  />
                </div>

                {!isLogin && (
                  <>
                    <div>
                      <Label htmlFor="full_name" className="font-medium">Full Name</Label>
                      <Input
                        id="full_name"
                        value={formData.full_name}
                        onChange={(e) => setFormData({...formData, full_name: e.target.value})}
                        required
                        className="mt-2 border-2 border-gray-200 focus:border-red-500 transition-colors"
                        placeholder="John Doe"
                      />
                    </div>
                    
                    <div>
                      <Label htmlFor="phone" className="font-medium">Phone Number</Label>
                      <Input
                        id="phone"
                        value={formData.phone}
                        onChange={(e) => setFormData({...formData, phone: e.target.value})}
                        className="mt-2 border-2 border-gray-200 focus:border-red-500 transition-colors"
                        placeholder="(555) 123-4567"
                      />
                    </div>
                    
                    <div>
                      <Label htmlFor="address" className="font-medium">Delivery Address (Optional)</Label>
                      <Textarea
                        id="address"
                        value={formData.address}
                        onChange={(e) => setFormData({...formData, address: e.target.value})}
                        className="mt-2 border-2 border-gray-200 focus:border-red-500 transition-colors"
                        placeholder="123 Main St, City, State"
                        rows={3}
                      />
                    </div>
                  </>
                )}

                <Button 
                  type="submit" 
                  className="w-full bg-red-600 hover:bg-red-700 py-3 text-lg font-medium shadow-lg hover:shadow-xl transition-all duration-300"
                  disabled={isLoading}
                >
                  {isLoading ? (
                    <div className="flex items-center">
                      <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white mr-2"></div>
                      Processing...
                    </div>
                  ) : (
                    <>
                      <CreditCard className="h-4 w-4 mr-2" />
                      {isLogin ? 'Sign In' : 'Create Account'}
                    </>
                  )}
                </Button>
              </form>
              
              <div className="mt-6 text-center">
                <button
                  type="button"
                  onClick={() => setIsLogin(!isLogin)}
                  className="text-red-600 hover:text-red-700 font-medium hover:underline transition-colors"
                >
                  {isLogin ? "Don't have an account? Sign up for free" : 'Already have an account? Sign in'}
                </button>
              </div>
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  );
};

// Enhanced Cart Page
const CartPage = () => {
  const { cartItems, updateQuantity, removeFromCart, clearCart, cartTotal } = useCart();
  const { user } = useAuth();
  const [isCheckingOut, setIsCheckingOut] = useState(false);
  const [orderDetails, setOrderDetails] = useState({
    phone: user?.phone || '',
    delivery_address: user?.address || '',
    notes: ''
  });

  const taxAmount = cartTotal * 0.08;
  const totalWithTax = cartTotal + taxAmount;

  const handleCheckout = async (e) => {
    e.preventDefault();
    
    if (!user) {
      toast.error('Please login to place an order');
      return;
    }

    try {
      setIsCheckingOut(true);
      
      const orderData = {
        items: cartItems.map(item => ({
          product_id: item.product_id,
          quantity: item.quantity,
          size: item.size,
          price: item.price
        })),
        phone: orderDetails.phone,
        delivery_address: orderDetails.delivery_address,
        notes: orderDetails.notes
      };

      await axios.post(`${API}/orders`, orderData);
      
      clearCart();
      toast.success('🎉 Order placed successfully! We\'ll have it ready soon.');
      setOrderDetails({ phone: '', delivery_address: '', notes: '' });
      
    } catch (error) {
      toast.error('Failed to place order. Please try again.');
    } finally {
      setIsCheckingOut(false);
    }
  };

  if (cartItems.length === 0) {
    return (
      <div className="min-h-screen bg-gray-50 py-16">
        <div className="container mx-auto px-4">
          <div className="max-w-md mx-auto text-center bg-white rounded-2xl shadow-lg p-12">
            <div className="bg-gray-100 rounded-full p-6 w-24 h-24 mx-auto mb-6">
              <ShoppingCart className="h-12 w-12 text-gray-400" />
            </div>
            <h2 className="text-2xl font-bold text-gray-800 mb-4">Your cart is empty</h2>
            <p className="text-gray-600 mb-8">Add some delicious items to get started on your order!</p>
            <Link to="/menu">
              <Button className="bg-red-600 hover:bg-red-700 px-8 py-3 text-lg">
                <Utensils className="h-5 w-5 mr-2" />
                Browse Menu
              </Button>
            </Link>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50 py-8">
      <div className="container mx-auto px-4">
        <div className="mb-8">
          <h1 className="text-3xl font-bold text-gray-800 mb-2">Your Order</h1>
          <p className="text-gray-600">Review your items and complete your order</p>
        </div>
        
        <div className="grid lg:grid-cols-3 gap-8">
          {/* Cart Items */}
          <div className="lg:col-span-2 space-y-4">
            <Card className="border-0 shadow-lg">
              <CardHeader className="pb-4">
                <CardTitle className="flex justify-between items-center">
                  <span>Order Items ({cartItems.length})</span>
                  <Button 
                    variant="outline" 
                    size="sm" 
                    onClick={clearCart}
                    className="text-red-600 border-red-200 hover:bg-red-50"
                  >
                    Clear All
                  </Button>
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                {cartItems.map((item) => (
                  <div key={item.key} className="flex items-center space-x-4 p-4 bg-gray-50 rounded-lg">
                    <img
                      src={item.image_url || "https://images.unsplash.com/photo-1565299624946-b28f40a0ae38"}
                      alt={item.name}
                      className="w-20 h-20 object-cover rounded-lg"
                    />
                    
                    <div className="flex-1">
                      <h3 className="font-semibold text-gray-800">{item.name}</h3>
                      {item.size && <p className="text-sm text-gray-600">Size: {item.size}</p>}
                      <p className="text-lg font-bold text-red-600">${item.price}</p>
                    </div>
                    
                    <div className="flex items-center space-x-3">
                      <Button
                        size="sm"
                        variant="outline"
                        onClick={() => updateQuantity(item.key, item.quantity - 1)}
                        className="h-8 w-8 p-0"
                      >
                        <Minus className="h-3 w-3" />
                      </Button>
                      <span className="px-3 py-1 bg-white border rounded font-medium min-w-[3rem] text-center">
                        {item.quantity}
                      </span>
                      <Button
                        size="sm"
                        variant="outline"
                        onClick={() => updateQuantity(item.key, item.quantity + 1)}
                        className="h-8 w-8 p-0"
                      >
                        <Plus className="h-3 w-3" />
                      </Button>
                    </div>
                    
                    <Button
                      size="sm"
                      variant="ghost"
                      onClick={() => removeFromCart(item.key)}
                      className="text-red-500 hover:text-red-700 hover:bg-red-50"
                    >
                      <X className="h-4 w-4" />
                    </Button>
                  </div>
                ))}
              </CardContent>
            </Card>
          </div>
          
          {/* Order Summary */}
          <div>
            <Card className="border-0 shadow-lg sticky top-8">
              <CardHeader>
                <CardTitle className="flex items-center">
                  <CreditCard className="h-5 w-5 mr-2" />
                  Order Summary
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="space-y-4 mb-6">
                  <div className="flex justify-between">
                    <span>Subtotal:</span>
                    <span>${cartTotal.toFixed(2)}</span>
                  </div>
                  <div className="flex justify-between">
                    <span>Tax (8%):</span>
                    <span>${taxAmount.toFixed(2)}</span>
                  </div>
                  <div className="flex justify-between">
                    <span>Delivery:</span>
                    <span className="text-green-600">Free</span>
                  </div>
                  <div className="border-t pt-4">
                    <div className="flex justify-between font-bold text-lg">
                      <span>Total:</span>
                      <span className="text-red-600">${totalWithTax.toFixed(2)}</span>
                    </div>
                  </div>
                </div>
                
                {user ? (
                  <form onSubmit={handleCheckout} className="space-y-4">
                    <div>
                      <Label htmlFor="phone" className="font-medium">Phone Number *</Label>
                      <Input
                        id="phone"
                        value={orderDetails.phone}
                        onChange={(e) => setOrderDetails({...orderDetails, phone: e.target.value})}
                        required
                        className="mt-2 border-2 border-gray-200 focus:border-red-500"
                        placeholder="(555) 123-4567"
                      />
                    </div>
                    
                    <div>
                      <Label htmlFor="delivery_address" className="font-medium">Delivery Address</Label>
                      <Textarea
                        id="delivery_address"
                        value={orderDetails.delivery_address}
                        onChange={(e) => setOrderDetails({...orderDetails, delivery_address: e.target.value})}
                        className="mt-2 border-2 border-gray-200 focus:border-red-500"
                        placeholder="Enter delivery address (leave blank for pickup)"
                        rows={3}
                      />
                    </div>
                    
                    <div>
                      <Label htmlFor="notes" className="font-medium">Special Instructions</Label>
                      <Textarea
                        id="notes"
                        value={orderDetails.notes}
                        onChange={(e) => setOrderDetails({...orderDetails, notes: e.target.value})}
                        className="mt-2 border-2 border-gray-200 focus:border-red-500"
                        placeholder="Any special requests..."
                        rows={2}
                      />
                    </div>
                    
                    <Button 
                      type="submit" 
                      className="w-full bg-red-600 hover:bg-red-700 py-3 text-lg font-medium shadow-lg hover:shadow-xl transition-all duration-300" 
                      disabled={isCheckingOut}
                    >
                      {isCheckingOut ? (
                        <div className="flex items-center">
                          <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white mr-2"></div>
                          Processing Order...
                        </div>
                      ) : (
                        <>
                          <CheckCircle2 className="h-5 w-5 mr-2" />
                          Place Order
                        </>
                      )}
                    </Button>
                  </form>
                ) : (
                  <div className="text-center">
                    <p className="text-gray-600 mb-4">Please login to place an order</p>
                    <Link to="/auth">
                      <Button className="bg-red-600 hover:bg-red-700 w-full py-3">
                        <User className="h-4 w-4 mr-2" />
                        Login to Continue
                      </Button>
                    </Link>
                  </div>
                )}
              </CardContent>
            </Card>
          </div>
        </div>
      </div>
    </div>
  );
};

// Orders Page
const OrdersPage = () => {
  const [orders, setOrders] = useState([]);
  const [isLoading, setIsLoading] = useState(true);
  const { user } = useAuth();

  useEffect(() => {
    if (user) {
      fetchOrders();
    }
  }, [user]);

  const fetchOrders = async () => {
    try {
      setIsLoading(true);
      const response = await axios.get(`${API}/orders`);
      setOrders(response.data);
    } catch (error) {
      console.error('Error fetching orders:', error);
      toast.error('Failed to load orders');
    } finally {
      setIsLoading(false);
    }
  };

  const getStatusColor = (status) => {
    const colors = {
      pending: 'bg-yellow-100 text-yellow-800',
      confirmed: 'bg-blue-100 text-blue-800',
      preparing: 'bg-orange-100 text-orange-800',
      ready: 'bg-green-100 text-green-800',
      delivered: 'bg-gray-100 text-gray-800',
      cancelled: 'bg-red-100 text-red-800'
    };
    return colors[status] || 'bg-gray-100 text-gray-800';
  };

  if (!user) {
    return (
      <div className="container mx-auto px-4 py-16 text-center">
        <h2 className="text-2xl font-bold text-gray-800 mb-4">Please Login</h2>
        <p className="text-gray-600 mb-8">You need to be logged in to view your orders</p>
        <Link to="/auth">
          <Button className="bg-red-600 hover:bg-red-700">Login</Button>
        </Link>
      </div>
    );
  }

  if (isLoading) {
    return (
      <div className="container mx-auto px-4 py-16">
        <div className="text-center">
          <div className="animate-spin rounded-full h-16 w-16 border-b-2 border-red-600 mx-auto mb-4"></div>
          <p className="text-gray-600">Loading your orders...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="container mx-auto px-4 py-8">
      <div className="mb-8">
        <h1 className="text-3xl font-bold text-gray-800 mb-2">Your Orders</h1>
        <p className="text-gray-600">Track your order status and history</p>
      </div>

      {orders.length === 0 ? (
        <div className="text-center py-16">
          <div className="bg-gray-100 rounded-full p-6 w-24 h-24 mx-auto mb-6">
            <Timer className="h-12 w-12 text-gray-400" />
          </div>
          <h3 className="text-xl font-medium text-gray-600 mb-2">No orders yet</h3>
          <p className="text-gray-500 mb-8">Start by placing your first order!</p>
          <Link to="/menu">
            <Button className="bg-red-600 hover:bg-red-700">Browse Menu</Button>
          </Link>
        </div>
      ) : (
        <div className="space-y-6">
          {orders.map((order) => (
            <Card key={order.id} className="border-0 shadow-lg">
              <CardHeader>
                <div className="flex justify-between items-start">
                  <div>
                    <CardTitle className="text-lg">Order #{order.id.slice(0, 8)}</CardTitle>
                    <CardDescription>
                      {new Date(order.created_at).toLocaleDateString()} at {new Date(order.created_at).toLocaleTimeString()}
                    </CardDescription>
                  </div>
                  <Badge className={getStatusColor(order.status)}>
                    {order.status.charAt(0).toUpperCase() + order.status.slice(1)}
                  </Badge>
                </div>
              </CardHeader>
              <CardContent>
                <div className="grid md:grid-cols-2 gap-6">
                  <div>
                    <h4 className="font-medium mb-3">Order Items</h4>
                    <div className="space-y-2">
                      {order.items.map((item, index) => (
                        <div key={index} className="flex justify-between text-sm">
                          <span>{item.quantity}x {item.product_id}</span>
                          <span>${(item.price * item.quantity).toFixed(2)}</span>
                        </div>
                      ))}
                    </div>
                  </div>
                  <div>
                    <h4 className="font-medium mb-3">Order Details</h4>
                    <div className="space-y-2 text-sm">
                      <div><strong>Phone:</strong> {order.phone}</div>
                      {order.delivery_address && (
                        <div><strong>Delivery:</strong> {order.delivery_address}</div>
                      )}
                      {order.notes && (
                        <div><strong>Notes:</strong> {order.notes}</div>
                      )}
                      <div className="pt-2 border-t">
                        <strong>Total: ${order.total_amount.toFixed(2)}</strong>
                      </div>
                    </div>
                  </div>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      )}
    </div>
  );
};

// Enhanced Admin Page
const AdminPage = () => {
  const { user } = useAuth();
  const [orders, setOrders] = useState([]);
  const [stats, setStats] = useState({
    totalOrders: 0,
    todayOrders: 0,
    revenue: 0
  });

  useEffect(() => {
    if (user?.is_admin) {
      fetchOrders();
    }
  }, [user]);

  const fetchOrders = async () => {
    try {
      const response = await axios.get(`${API}/orders`);
      const ordersData = response.data;
      setOrders(ordersData);
      
      // Calculate stats
      const today = new Date().toDateString();
      const todayOrders = ordersData.filter(order => 
        new Date(order.created_at).toDateString() === today
      );
      
      setStats({
        totalOrders: ordersData.length,
        todayOrders: todayOrders.length,
        revenue: ordersData.reduce((sum, order) => sum + order.total_amount, 0)
      });
    } catch (error) {
      console.error('Error fetching orders:', error);
      toast.error('Failed to load orders');
    }
  };

  const updateOrderStatus = async (orderId, status) => {
    try {
      await axios.put(`${API}/orders/${orderId}/status`, null, {
        params: { status }
      });
      toast.success('Order status updated successfully');
      fetchOrders();
    } catch (error) {
      toast.error('Failed to update order status');
    }
  };

  if (!user?.is_admin) {
    return (
      <div className="container mx-auto px-4 py-16 text-center">
        <div className="bg-red-50 border border-red-200 rounded-lg p-8 max-w-md mx-auto">
          <h2 className="text-2xl font-bold text-red-800 mb-4">Access Denied</h2>
          <p className="text-red-600">You need admin privileges to access this page.</p>
        </div>
      </div>
    );
  }

  return (
    <div className="container mx-auto px-4 py-8">
      <div className="mb-8">
        <h1 className="text-3xl font-bold text-gray-800 mb-2">Admin Dashboard</h1>
        <p className="text-gray-600">Manage orders and monitor restaurant performance</p>
      </div>

      {/* Stats Cards */}
      <div className="grid md:grid-cols-3 gap-6 mb-8">
        <Card className="border-0 shadow-lg">
          <CardContent className="pt-6">
            <div className="flex items-center">
              <div className="bg-blue-500 p-3 rounded-lg">
                <TrendingUp className="h-6 w-6 text-white" />
              </div>
              <div className="ml-4">
                <p className="text-sm font-medium text-gray-600">Total Orders</p>
                <p className="text-2xl font-bold text-gray-900">{stats.totalOrders}</p>
              </div>
            </div>
          </CardContent>
        </Card>

        <Card className="border-0 shadow-lg">
          <CardContent className="pt-6">
            <div className="flex items-center">
              <div className="bg-green-500 p-3 rounded-lg">
                <Timer className="h-6 w-6 text-white" />
              </div>
              <div className="ml-4">
                <p className="text-sm font-medium text-gray-600">Today's Orders</p>
                <p className="text-2xl font-bold text-gray-900">{stats.todayOrders}</p>
              </div>
            </div>
          </CardContent>
        </Card>

        <Card className="border-0 shadow-lg">
          <CardContent className="pt-6">
            <div className="flex items-center">
              <div className="bg-red-500 p-3 rounded-lg">
                <CreditCard className="h-6 w-6 text-white" />
              </div>
              <div className="ml-4">
                <p className="text-sm font-medium text-gray-600">Total Revenue</p>
                <p className="text-2xl font-bold text-gray-900">${stats.revenue.toFixed(2)}</p>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>
      
      <Tabs defaultValue="orders" className="space-y-6">
        <TabsList className="grid w-full grid-cols-2">
          <TabsTrigger value="orders">Recent Orders</TabsTrigger>
          <TabsTrigger value="products">Products</TabsTrigger>
        </TabsList>
        
        <TabsContent value="orders" className="space-y-4">
          <Card className="border-0 shadow-lg">
            <CardHeader>
              <CardTitle>Recent Orders</CardTitle>
            </CardHeader>
            <CardContent>
              {orders.length === 0 ? (
                <p className="text-gray-500 text-center py-8">No orders found</p>
              ) : (
                <div className="space-y-4">
                  {orders.slice(0, 10).map((order) => (
                    <div key={order.id} className="border rounded-lg p-4">
                      <div className="flex justify-between items-start mb-4">
                        <div>
                          <h3 className="font-semibold">Order #{order.id.slice(0, 8)}</h3>
                          <p className="text-sm text-gray-600">
                            {new Date(order.created_at).toLocaleString()}
                          </p>
                          <p className="text-sm text-gray-600">Phone: {order.phone}</p>
                          <p className="text-sm font-medium">Total: ${order.total_amount.toFixed(2)}</p>
                        </div>
                        
                        <div className="flex items-center space-x-4">
                          <Select
                            value={order.status}
                            onValueChange={(status) => updateOrderStatus(order.id, status)}
                          >
                            <SelectTrigger className="w-32">
                              <SelectValue />
                            </SelectTrigger>
                            <SelectContent>
                              <SelectItem value="pending">Pending</SelectItem>
                              <SelectItem value="confirmed">Confirmed</SelectItem>
                              <SelectItem value="preparing">Preparing</SelectItem>
                              <SelectItem value="ready">Ready</SelectItem>
                              <SelectItem value="delivered">Delivered</SelectItem>
                              <SelectItem value="cancelled">Cancelled</SelectItem>
                            </SelectContent>
                          </Select>
                        </div>
                      </div>
                      
                      <div className="text-sm text-gray-600">
                        <strong>Items:</strong> {order.items.map(item => 
                          `${item.quantity}x ${item.product_id}`
                        ).join(', ')}
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </CardContent>
          </Card>
        </TabsContent>
        
        <TabsContent value="products">
          <Card className="border-0 shadow-lg">
            <CardContent className="pt-6">
              <div className="text-center py-12">
                <ChefHat className="h-16 w-16 text-gray-300 mx-auto mb-4" />
                <p className="text-gray-600 text-lg">Product management coming soon...</p>
                <p className="text-gray-500">Add, edit, and manage your menu items</p>
              </div>
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  );
};

// Main App
function App() {
  // Initialize complete menu data on app start
  useEffect(() => {
    const initializeData = async () => {
      try {
        await axios.post(`${API}/init-data`);
      } catch (error) {
        console.error('Error initializing data:', error);
      }
    };

    initializeData();
  }, []);

  return (
    <AuthProvider>
      <CartProvider>
        <div className="App">
          <BrowserRouter>
            <Header />
            <main>
              <Routes>
                <Route path="/" element={<HomePage />} />
                <Route path="/menu" element={<MenuPage />} />
                <Route path="/cart" element={<CartPage />} />
                <Route path="/orders" element={<OrdersPage />} />
                <Route path="/auth" element={<AuthPage />} />
                <Route path="/admin" element={<AdminPage />} />
              </Routes>
            </main>
          </BrowserRouter>
        </div>
      </CartProvider>
    </AuthProvider>
  );
}

export default App;