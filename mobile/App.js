// React Native Version - I Love NY Pizza
import React, { useState, useEffect, createContext, useContext } from 'react';
import {
  StyleSheet,
  Text,
  View,
  ScrollView,
  TouchableOpacity,
  Image,
  TextInput,
  Alert,
  FlatList,
  SafeAreaView,
  StatusBar,
  Platform,
  Dimensions
} from 'react-native';
import AsyncStorage from '@react-native-async-storage/async-storage';
import PushNotification from 'react-native-push-notification';
import { NavigationContainer } from '@react-navigation/native';
import { createStackNavigator } from '@react-navigation/stack';
import { createBottomTabNavigator } from '@react-navigation/bottom-tabs';
import Icon from 'react-native-vector-icons/MaterialIcons';

const { width, height } = Dimensions.get('window');
const Stack = createStackNavigator();
const Tab = createBottomTabNavigator();

// API Configuration
const API_BASE_URL = 'https://crust-corner.preview.emergentagent.com/api';

// Auth Context
const AuthContext = createContext();

const AuthProvider = ({ children }) => {
  const [user, setUser] = useState(null);
  const [token, setToken] = useState(null);

  useEffect(() => {
    loadStoredAuth();
    setupPushNotifications();
  }, []);

  const loadStoredAuth = async () => {
    try {
      const storedToken = await AsyncStorage.getItem('token');
      const storedUser = await AsyncStorage.getItem('user');
      if (storedToken && storedUser) {
        setToken(storedToken);
        setUser(JSON.parse(storedUser));
      }
    } catch (error) {
      console.error('Error loading stored auth:', error);
    }
  };

  const login = async (userData, tokenData) => {
    try {
      await AsyncStorage.setItem('token', tokenData);
      await AsyncStorage.setItem('user', JSON.stringify(userData));
      setUser(userData);
      setToken(tokenData);
    } catch (error) {
      console.error('Error storing auth:', error);
    }
  };

  const logout = async () => {
    try {
      await AsyncStorage.removeItem('token');
      await AsyncStorage.removeItem('user');
      setUser(null);
      setToken(null);
    } catch (error) {
      console.error('Error removing auth:', error);
    }
  };

  const setupPushNotifications = () => {
    PushNotification.configure({
      onNotification: function(notification) {
        console.log('NOTIFICATION:', notification);
      },
      requestPermissions: Platform.OS === 'ios',
    });
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
    
    Alert.alert('Success', 'Added to cart!');
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
  };

  const clearCart = () => setCartItems([]);

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
      cartCount 
    }}>
      {children}
    </CartContext.Provider>
  );
};

const useCart = () => useContext(CartContext);

// Home Screen
const HomeScreen = ({ navigation }) => {
  const [featuredProducts, setFeaturedProducts] = useState([]);

  useEffect(() => {
    fetchFeaturedProducts();
  }, []);

  const fetchFeaturedProducts = async () => {
    try {
      const response = await fetch(`${API_BASE_URL}/products?featured=true`);
      const data = await response.json();
      setFeaturedProducts(data);
    } catch (error) {
      console.error('Error fetching featured products:', error);
    }
  };

  const renderFeaturedProduct = ({ item }) => (
    <TouchableOpacity 
      style={styles.featuredCard}
      onPress={() => navigation.navigate('ProductDetail', { product: item })}
    >
      <Image source={{ uri: item.image_url }} style={styles.featuredImage} />
      <View style={styles.featuredInfo}>
        <Text style={styles.featuredName}>{item.name}</Text>
        <Text style={styles.featuredPrice}>${item.price}</Text>
      </View>
    </TouchableOpacity>
  );

  return (
    <SafeAreaView style={styles.container}>
      <ScrollView>
        {/* Hero Section */}
        <View style={styles.hero}>
          <Image
            source={{ uri: 'https://images.unsplash.com/photo-1593504049359-74330189a345' }}
            style={styles.heroImage}
          />
          <View style={styles.heroOverlay}>
            <Text style={styles.heroTitle}>Authentic New York Pizza</Text>
            <Text style={styles.heroSubtitle}>Fresh ingredients, delivered hot!</Text>
            <TouchableOpacity 
              style={styles.orderButton}
              onPress={() => navigation.navigate('Menu')}
            >
              <Text style={styles.orderButtonText}>Order Now</Text>
            </TouchableOpacity>
          </View>
        </View>

        {/* Featured Products */}
        <View style={styles.section}>
          <Text style={styles.sectionTitle}>Featured Favorites</Text>
          <FlatList
            data={featuredProducts}
            renderItem={renderFeaturedProduct}
            keyExtractor={item => item.id}
            horizontal
            showsHorizontalScrollIndicator={false}
            contentContainerStyle={styles.featuredList}
          />
        </View>

        {/* Quick Actions */}
        <View style={styles.quickActions}>
          <TouchableOpacity 
            style={styles.quickAction}
            onPress={() => navigation.navigate('Menu')}
          >
            <Icon name="restaurant-menu" size={30} color="#dc2626" />
            <Text style={styles.quickActionText}>Full Menu</Text>
          </TouchableOpacity>
          
          <TouchableOpacity 
            style={styles.quickAction}
            onPress={() => navigation.navigate('Orders')}
          >
            <Icon name="history" size={30} color="#dc2626" />
            <Text style={styles.quickActionText}>Order History</Text>
          </TouchableOpacity>
          
          <TouchableOpacity style={styles.quickAction}>
            <Icon name="phone" size={30} color="#dc2626" />
            <Text style={styles.quickActionText}>Call Us</Text>
          </TouchableOpacity>
        </View>
      </ScrollView>
    </SafeAreaView>
  );
};

// Menu Screen
const MenuScreen = ({ navigation }) => {
  const [products, setProducts] = useState([]);
  const [categories, setCategories] = useState([]);
  const [selectedCategory, setSelectedCategory] = useState('all');
  const [searchQuery, setSearchQuery] = useState('');
  const { addToCart } = useCart();

  useEffect(() => {
    fetchProducts();
    fetchCategories();
  }, []);

  const fetchProducts = async () => {
    try {
      const response = await fetch(`${API_BASE_URL}/products`);
      const data = await response.json();
      setProducts(data);
    } catch (error) {
      console.error('Error fetching products:', error);
    }
  };

  const fetchCategories = async () => {
    try {
      const response = await fetch(`${API_BASE_URL}/categories`);
      const data = await response.json();
      setCategories(data);
    } catch (error) {
      console.error('Error fetching categories:', error);
    }
  };

  const filteredProducts = products.filter(product => {
    const matchesCategory = selectedCategory === 'all' || product.category_id === selectedCategory;
    const matchesSearch = product.name.toLowerCase().includes(searchQuery.toLowerCase());
    return matchesCategory && matchesSearch;
  });

  const renderProduct = ({ item }) => (
    <TouchableOpacity 
      style={styles.productCard}
      onPress={() => navigation.navigate('ProductDetail', { product: item })}
    >
      <Image source={{ uri: item.image_url }} style={styles.productImage} />
      <View style={styles.productInfo}>
        <Text style={styles.productName}>{item.name}</Text>
        <Text style={styles.productDescription} numberOfLines={2}>{item.description}</Text>
        <View style={styles.productFooter}>
          <Text style={styles.productPrice}>${item.price}</Text>
          <TouchableOpacity 
            style={styles.addButton}
            onPress={() => addToCart(item)}
          >
            <Icon name="add" size={20} color="white" />
          </TouchableOpacity>
        </View>
      </View>
    </TouchableOpacity>
  );

  const renderCategory = ({ item }) => (
    <TouchableOpacity
      style={[
        styles.categoryChip,
        selectedCategory === item.id && styles.categoryChipActive
      ]}
      onPress={() => setSelectedCategory(item.id)}
    >
      <Text style={[
        styles.categoryChipText,
        selectedCategory === item.id && styles.categoryChipTextActive
      ]}>
        {item.name}
      </Text>
    </TouchableOpacity>
  );

  return (
    <SafeAreaView style={styles.container}>
      {/* Search Bar */}
      <View style={styles.searchContainer}>
        <Icon name="search" size={20} color="#666" style={styles.searchIcon} />
        <TextInput
          style={styles.searchInput}
          placeholder="Search for food..."
          value={searchQuery}
          onChangeText={setSearchQuery}
        />
      </View>

      {/* Categories */}
      <FlatList
        data={[{ id: 'all', name: 'All' }, ...categories]}
        renderItem={renderCategory}
        keyExtractor={item => item.id}
        horizontal
        showsHorizontalScrollIndicator={false}
        style={styles.categoriesList}
      />

      {/* Products */}
      <FlatList
        data={filteredProducts}
        renderItem={renderProduct}
        keyExtractor={item => item.id}
        numColumns={2}
        columnWrapperStyle={styles.productRow}
        contentContainerStyle={styles.productsList}
      />
    </SafeAreaView>
  );
};

// Product Detail Screen
const ProductDetailScreen = ({ route, navigation }) => {
  const { product } = route.params;
  const [selectedSize, setSelectedSize] = useState(
    product.sizes && product.sizes.length > 0 ? product.sizes[0] : null
  );
  const { addToCart } = useCart();

  const handleAddToCart = () => {
    addToCart(product, selectedSize);
    navigation.goBack();
  };

  return (
    <SafeAreaView style={styles.container}>
      <ScrollView>
        <Image source={{ uri: product.image_url }} style={styles.detailImage} />
        
        <View style={styles.detailContent}>
          <Text style={styles.detailName}>{product.name}</Text>
          <Text style={styles.detailDescription}>{product.description}</Text>
          
          {product.ingredients && (
            <View style={styles.ingredientsContainer}>
              <Text style={styles.ingredientsTitle}>Ingredients:</Text>
              <Text style={styles.ingredientsText}>{product.ingredients.join(', ')}</Text>
            </View>
          )}

          {product.sizes && product.sizes.length > 0 && (
            <View style={styles.sizesContainer}>
              <Text style={styles.sizesTitle}>Size Options:</Text>
              {product.sizes.map((size, index) => (
                <TouchableOpacity
                  key={index}
                  style={[
                    styles.sizeOption,
                    selectedSize?.name === size.name && styles.sizeOptionActive
                  ]}
                  onPress={() => setSelectedSize(size)}
                >
                  <Text style={styles.sizeName}>{size.name}</Text>
                  <Text style={styles.sizePrice}>${size.price}</Text>
                </TouchableOpacity>
              ))}
            </View>
          )}

          <View style={styles.priceContainer}>
            <Text style={styles.finalPrice}>
              ${selectedSize ? selectedSize.price : product.price}
            </Text>
          </View>

          <TouchableOpacity style={styles.addToCartButton} onPress={handleAddToCart}>
            <Text style={styles.addToCartText}>Add to Cart</Text>
          </TouchableOpacity>
        </View>
      </ScrollView>
    </SafeAreaView>
  );
};

// Cart Screen
const CartScreen = ({ navigation }) => {
  const { cartItems, updateQuantity, removeFromCart, cartTotal } = useCart();
  const { user } = useAuth();

  const renderCartItem = ({ item }) => (
    <View style={styles.cartItem}>
      <Image source={{ uri: item.image_url }} style={styles.cartItemImage} />
      <View style={styles.cartItemInfo}>
        <Text style={styles.cartItemName}>{item.name}</Text>
        {item.size && <Text style={styles.cartItemSize}>Size: {item.size}</Text>}
        <Text style={styles.cartItemPrice}>${item.price}</Text>
      </View>
      <View style={styles.quantityContainer}>
        <TouchableOpacity 
          style={styles.quantityButton}
          onPress={() => updateQuantity(item.key, item.quantity - 1)}
        >
          <Icon name="remove" size={16} color="white" />
        </TouchableOpacity>
        <Text style={styles.quantityText}>{item.quantity}</Text>
        <TouchableOpacity 
          style={styles.quantityButton}
          onPress={() => updateQuantity(item.key, item.quantity + 1)}
        >
          <Icon name="add" size={16} color="white" />
        </TouchableOpacity>
      </View>
    </View>
  );

  if (cartItems.length === 0) {
    return (
      <SafeAreaView style={[styles.container, styles.emptyContainer]}>
        <Icon name="shopping-cart" size={80} color="#ccc" />
        <Text style={styles.emptyText}>Your cart is empty</Text>
        <TouchableOpacity 
          style={styles.browseButton}
          onPress={() => navigation.navigate('Menu')}
        >
          <Text style={styles.browseButtonText}>Browse Menu</Text>
        </TouchableOpacity>
      </SafeAreaView>
    );
  }

  return (
    <SafeAreaView style={styles.container}>
      <FlatList
        data={cartItems}
        renderItem={renderCartItem}
        keyExtractor={item => item.key}
        style={styles.cartList}
      />
      
      <View style={styles.cartFooter}>
        <View style={styles.totalContainer}>
          <Text style={styles.totalLabel}>Total:</Text>
          <Text style={styles.totalAmount}>${cartTotal.toFixed(2)}</Text>
        </View>
        
        <TouchableOpacity 
          style={styles.checkoutButton}
          onPress={() => user ? navigation.navigate('Checkout') : navigation.navigate('Auth')}
        >
          <Text style={styles.checkoutText}>
            {user ? 'Proceed to Checkout' : 'Login to Checkout'}
          </Text>
        </TouchableOpacity>
      </View>
    </SafeAreaView>
  );
};

// Auth Screen
const AuthScreen = ({ navigation }) => {
  const [isLogin, setIsLogin] = useState(true);
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [fullName, setFullName] = useState('');
  const [phone, setPhone] = useState('');
  const { login } = useAuth();

  const handleSubmit = async () => {
    try {
      const endpoint = isLogin ? '/auth/login' : '/auth/register';
      const body = isLogin 
        ? { email, password }
        : { email, password, full_name: fullName, phone };

      const response = await fetch(`${API_BASE_URL}${endpoint}`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(body),
      });

      const data = await response.json();
      
      if (response.ok) {
        await login(data.user, data.token);
        Alert.alert('Success', isLogin ? 'Logged in successfully!' : 'Account created successfully!');
        navigation.goBack();
      } else {
        Alert.alert('Error', data.detail || 'Something went wrong');
      }
    } catch (error) {
      Alert.alert('Error', 'Network error. Please try again.');
    }
  };

  return (
    <SafeAreaView style={styles.container}>
      <ScrollView contentContainerStyle={styles.authContainer}>
        <Text style={styles.authTitle}>{isLogin ? 'Welcome Back!' : 'Create Account'}</Text>
        
        <TextInput
          style={styles.input}
          placeholder="Email"
          value={email}
          onChangeText={setEmail}
          keyboardType="email-address"
          autoCapitalize="none"
        />
        
        <TextInput
          style={styles.input}
          placeholder="Password"
          value={password}
          onChangeText={setPassword}
          secureTextEntry
        />
        
        {!isLogin && (
          <>
            <TextInput
              style={styles.input}
              placeholder="Full Name"
              value={fullName}
              onChangeText={setFullName}
            />
            <TextInput
              style={styles.input}
              placeholder="Phone Number"
              value={phone}
              onChangeText={setPhone}
              keyboardType="phone-pad"
            />
          </>
        )}
        
        <TouchableOpacity style={styles.submitButton} onPress={handleSubmit}>
          <Text style={styles.submitButtonText}>
            {isLogin ? 'Sign In' : 'Create Account'}
          </Text>
        </TouchableOpacity>
        
        <TouchableOpacity onPress={() => setIsLogin(!isLogin)}>
          <Text style={styles.switchText}>
            {isLogin ? "Don't have an account? Sign up" : 'Already have an account? Sign in'}
          </Text>
        </TouchableOpacity>
      </ScrollView>
    </SafeAreaView>
  );
};

// Profile Screen
const ProfileScreen = ({ navigation }) => {
  const { user, logout } = useAuth();

  if (!user) {
    return (
      <SafeAreaView style={[styles.container, styles.emptyContainer]}>
        <Icon name="person" size={80} color="#ccc" />
        <Text style={styles.emptyText}>Please login to view profile</Text>
        <TouchableOpacity 
          style={styles.browseButton}
          onPress={() => navigation.navigate('Auth')}
        >
          <Text style={styles.browseButtonText}>Login</Text>
        </TouchableOpacity>
      </SafeAreaView>
    );
  }

  const handleLogout = () => {
    Alert.alert(
      'Logout',
      'Are you sure you want to logout?',
      [
        { text: 'Cancel', style: 'cancel' },
        { text: 'Logout', onPress: logout }
      ]
    );
  };

  return (
    <SafeAreaView style={styles.container}>
      <View style={styles.profileContainer}>
        <View style={styles.profileHeader}>
          <Icon name="person" size={60} color="#dc2626" />
          <Text style={styles.profileName}>{user.full_name}</Text>
          <Text style={styles.profileEmail}>{user.email}</Text>
        </View>
        
        <View style={styles.profileMenu}>
          <TouchableOpacity 
            style={styles.menuItem}
            onPress={() => navigation.navigate('Orders')}
          >
            <Icon name="history" size={24} color="#666" />
            <Text style={styles.menuItemText}>Order History</Text>
            <Icon name="chevron-right" size={24} color="#ccc" />
          </TouchableOpacity>
          
          <TouchableOpacity style={styles.menuItem}>
            <Icon name="favorite" size={24} color="#666" />
            <Text style={styles.menuItemText}>Favorites</Text>
            <Icon name="chevron-right" size={24} color="#ccc" />
          </TouchableOpacity>
          
          <TouchableOpacity style={styles.menuItem}>
            <Icon name="location-on" size={24} color="#666" />
            <Text style={styles.menuItemText}>Addresses</Text>
            <Icon name="chevron-right" size={24} color="#ccc" />
          </TouchableOpacity>
          
          <TouchableOpacity style={styles.menuItem}>
            <Icon name="payment" size={24} color="#666" />
            <Text style={styles.menuItemText}>Payment Methods</Text>
            <Icon name="chevron-right" size={24} color="#ccc" />
          </TouchableOpacity>
          
          <TouchableOpacity style={styles.menuItem} onPress={handleLogout}>
            <Icon name="logout" size={24} color="#dc2626" />
            <Text style={[styles.menuItemText, styles.logoutText]}>Logout</Text>
          </TouchableOpacity>
        </View>
      </View>
    </SafeAreaView>
  );
};

// Tab Navigator
const TabNavigator = () => {
  const { cartCount } = useCart();

  return (
    <Tab.Navigator
      screenOptions={({ route }) => ({
        tabBarIcon: ({ focused, color, size }) => {
          let iconName;

          if (route.name === 'Home') {
            iconName = 'home';
          } else if (route.name === 'Menu') {
            iconName = 'restaurant-menu';
          } else if (route.name === 'Cart') {
            iconName = 'shopping-cart';
          } else if (route.name === 'Profile') {
            iconName = 'person';
          }

          return <Icon name={iconName} size={size} color={color} />;
        },
        tabBarActiveTintColor: '#dc2626',
        tabBarInactiveTintColor: 'gray',
        headerShown: false,
      })}
    >
      <Tab.Screen name="Home" component={HomeScreen} />
      <Tab.Screen name="Menu" component={MenuScreen} />
      <Tab.Screen 
        name="Cart" 
        component={CartScreen} 
        options={{
          tabBarBadge: cartCount > 0 ? cartCount : null,
        }}
      />
      <Tab.Screen name="Profile" component={ProfileScreen} />
    </Tab.Navigator>
  );
};

// Main App
const App = () => {
  return (
    <AuthProvider>
      <CartProvider>
        <NavigationContainer>
          <StatusBar barStyle="dark-content" backgroundColor="#ffffff" />
          <Stack.Navigator screenOptions={{ headerShown: false }}>
            <Stack.Screen name="Tabs" component={TabNavigator} />
            <Stack.Screen name="ProductDetail" component={ProductDetailScreen} />
            <Stack.Screen name="Auth" component={AuthScreen} />
          </Stack.Navigator>
        </NavigationContainer>
      </CartProvider>
    </AuthProvider>
  );
};

// Styles
const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#fff',
  },
  hero: {
    height: 200,
    position: 'relative',
  },
  heroImage: {
    width: '100%',
    height: '100%',
    resizeMode: 'cover',
  },
  heroOverlay: {
    position: 'absolute',
    top: 0,
    left: 0,
    right: 0,
    bottom: 0,
    backgroundColor: 'rgba(0, 0, 0, 0.4)',
    justifyContent: 'center',
    alignItems: 'center',
    paddingHorizontal: 20,
  },
  heroTitle: {
    fontSize: 24,
    fontWeight: 'bold',
    color: 'white',
    textAlign: 'center',
    marginBottom: 8,
  },
  heroSubtitle: {
    fontSize: 16,
    color: 'white',
    textAlign: 'center',
    marginBottom: 20,
  },
  orderButton: {
    backgroundColor: '#dc2626',
    paddingHorizontal: 30,
    paddingVertical: 12,
    borderRadius: 25,
  },
  orderButtonText: {
    color: 'white',
    fontSize: 16,
    fontWeight: 'bold',
  },
  section: {
    padding: 20,
  },
  sectionTitle: {
    fontSize: 20,
    fontWeight: 'bold',
    marginBottom: 15,
    color: '#333',
  },
  featuredList: {
    paddingLeft: 5,
  },
  featuredCard: {
    width: 150,
    marginRight: 15,
    backgroundColor: '#f9f9f9',
    borderRadius: 10,
    overflow: 'hidden',
  },
  featuredImage: {
    width: '100%',
    height: 100,
    resizeMode: 'cover',
  },
  featuredInfo: {
    padding: 10,
  },
  featuredName: {
    fontSize: 14,
    fontWeight: '600',
    marginBottom: 5,
  },
  featuredPrice: {
    fontSize: 16,
    fontWeight: 'bold',
    color: '#dc2626',
  },
  quickActions: {
    flexDirection: 'row',
    justifyContent: 'space-around',
    paddingHorizontal: 20,
    paddingVertical: 30,
    backgroundColor: '#f9f9f9',
  },
  quickAction: {
    alignItems: 'center',
  },
  quickActionText: {
    marginTop: 8,
    fontSize: 12,
    color: '#666',
  },
  searchContainer: {
    flexDirection: 'row',
    alignItems: 'center',
    margin: 15,
    paddingHorizontal: 15,
    paddingVertical: 10,
    backgroundColor: '#f0f0f0',
    borderRadius: 25,
  },
  searchIcon: {
    marginRight: 10,
  },
  searchInput: {
    flex: 1,
    fontSize: 16,
  },
  categoriesList: {
    paddingHorizontal: 15,
    marginBottom: 10,
  },
  categoryChip: {
    paddingHorizontal: 15,
    paddingVertical: 8,
    marginRight: 10,
    backgroundColor: '#f0f0f0',
    borderRadius: 20,
  },
  categoryChipActive: {
    backgroundColor: '#dc2626',
  },
  categoryChipText: {
    color: '#666',
    fontSize: 14,
  },
  categoryChipTextActive: {
    color: 'white',
  },
  productsList: {
    paddingHorizontal: 10,
  },
  productRow: {
    justifyContent: 'space-between',
  },
  productCard: {
    width: (width - 30) / 2,
    backgroundColor: '#fff',
    borderRadius: 10,
    marginBottom: 15,
    elevation: 2,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 1 },
    shadowOpacity: 0.2,
    shadowRadius: 2,
  },
  productImage: {
    width: '100%',
    height: 120,
    borderTopLeftRadius: 10,
    borderTopRightRadius: 10,
    resizeMode: 'cover',
  },
  productInfo: {
    padding: 10,
  },
  productName: {
    fontSize: 14,
    fontWeight: '600',
    marginBottom: 5,
  },
  productDescription: {
    fontSize: 12,
    color: '#666',
    marginBottom: 10,
  },
  productFooter: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
  },
  productPrice: {
    fontSize: 16,
    fontWeight: 'bold',
    color: '#dc2626',
  },
  addButton: {
    backgroundColor: '#dc2626',
    width: 30,
    height: 30,
    borderRadius: 15,
    justifyContent: 'center',
    alignItems: 'center',
  },
  detailImage: {
    width: '100%',
    height: 250,
    resizeMode: 'cover',
  },
  detailContent: {
    padding: 20,
  },
  detailName: {
    fontSize: 24,
    fontWeight: 'bold',
    marginBottom: 10,
  },
  detailDescription: {
    fontSize: 16,
    color: '#666',
    marginBottom: 20,
  },
  ingredientsContainer: {
    marginBottom: 20,
  },
  ingredientsTitle: {
    fontSize: 16,
    fontWeight: '600',
    marginBottom: 5,
  },
  ingredientsText: {
    fontSize: 14,
    color: '#666',
  },
  sizesContainer: {
    marginBottom: 20,
  },
  sizesTitle: {
    fontSize: 16,
    fontWeight: '600',
    marginBottom: 10,
  },
  sizeOption: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    paddingVertical: 12,
    paddingHorizontal: 15,
    marginBottom: 8,
    backgroundColor: '#f9f9f9',
    borderRadius: 8,
  },
  sizeOptionActive: {
    backgroundColor: '#dc2626',
  },
  sizeName: {
    fontSize: 14,
    fontWeight: '500',
  },
  sizePrice: {
    fontSize: 16,
    fontWeight: 'bold',
    color: '#dc2626',
  },
  priceContainer: {
    alignItems: 'center',
    marginBottom: 30,
  },
  finalPrice: {
    fontSize: 28,
    fontWeight: 'bold',
    color: '#dc2626',
  },
  addToCartButton: {
    backgroundColor: '#dc2626',
    paddingVertical: 15,
    borderRadius: 10,
    alignItems: 'center',
  },
  addToCartText: {
    color: 'white',
    fontSize: 18,
    fontWeight: 'bold',
  },
  emptyContainer: {
    justifyContent: 'center',
    alignItems: 'center',
  },
  emptyText: {
    fontSize: 18,
    color: '#666',
    marginVertical: 20,
  },
  browseButton: {
    backgroundColor: '#dc2626',
    paddingHorizontal: 30,
    paddingVertical: 12,
    borderRadius: 25,
  },
  browseButtonText: {
    color: 'white',
    fontSize: 16,
    fontWeight: 'bold',
  },
  cartList: {
    flex: 1,
    paddingHorizontal: 15,
  },
  cartItem: {
    flexDirection: 'row',
    backgroundColor: '#fff',
    padding: 15,
    marginVertical: 5,
    borderRadius: 10,
    elevation: 1,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 1 },
    shadowOpacity: 0.1,
    shadowRadius: 1,
  },
  cartItemImage: {
    width: 60,
    height: 60,
    borderRadius: 8,
    resizeMode: 'cover',
  },
  cartItemInfo: {
    flex: 1,
    marginLeft: 15,
    justifyContent: 'center',
  },
  cartItemName: {
    fontSize: 16,
    fontWeight: '600',
    marginBottom: 2,
  },
  cartItemSize: {
    fontSize: 12,
    color: '#666',
    marginBottom: 2,
  },
  cartItemPrice: {
    fontSize: 16,
    fontWeight: 'bold',
    color: '#dc2626',
  },
  quantityContainer: {
    flexDirection: 'row',
    alignItems: 'center',
  },
  quantityButton: {
    backgroundColor: '#dc2626',
    width: 25,
    height: 25,
    borderRadius: 12.5,
    justifyContent: 'center',
    alignItems: 'center',
  },
  quantityText: {
    marginHorizontal: 15,
    fontSize: 16,
    fontWeight: '600',
  },
  cartFooter: {
    padding: 20,
    backgroundColor: '#f9f9f9',
    borderTopWidth: 1,
    borderTopColor: '#eee',
  },
  totalContainer: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 20,
  },
  totalLabel: {
    fontSize: 18,
    fontWeight: '600',
  },
  totalAmount: {
    fontSize: 24,
    fontWeight: 'bold',
    color: '#dc2626',
  },
  checkoutButton: {
    backgroundColor: '#dc2626',
    paddingVertical: 15,
    borderRadius: 10,
    alignItems: 'center',
  },
  checkoutText: {
    color: 'white',
    fontSize: 18,
    fontWeight: 'bold',
  },
  authContainer: {
    padding: 30,
    justifyContent: 'center',
    minHeight: height - 100,
  },
  authTitle: {
    fontSize: 28,
    fontWeight: 'bold',
    textAlign: 'center',
    marginBottom: 30,
    color: '#333',
  },
  input: {
    borderWidth: 1,
    borderColor: '#ddd',
    borderRadius: 10,
    paddingHorizontal: 15,
    paddingVertical: 12,
    fontSize: 16,
    marginBottom: 15,
  },
  submitButton: {
    backgroundColor: '#dc2626',
    paddingVertical: 15,
    borderRadius: 10,
    alignItems: 'center',
    marginTop: 10,
  },
  submitButtonText: {
    color: 'white',
    fontSize: 18,
    fontWeight: 'bold',
  },
  switchText: {
    textAlign: 'center',
    marginTop: 20,
    color: '#dc2626',
    fontSize: 16,
  },
  profileContainer: {
    flex: 1,
  },
  profileHeader: {
    alignItems: 'center',
    paddingVertical: 40,
    backgroundColor: '#f9f9f9',
  },
  profileName: {
    fontSize: 24,
    fontWeight: 'bold',
    marginTop: 10,
    color: '#333',
  },
  profileEmail: {
    fontSize: 16,
    color: '#666',
    marginTop: 5,
  },
  profileMenu: {
    flex: 1,
    paddingTop: 20,
  },
  menuItem: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingHorizontal: 20,
    paddingVertical: 15,
    borderBottomWidth: 1,
    borderBottomColor: '#eee',
  },
  menuItemText: {
    flex: 1,
    fontSize: 16,
    marginLeft: 15,
    color: '#333',
  },
  logoutText: {
    color: '#dc2626',
  },
});

export default App;