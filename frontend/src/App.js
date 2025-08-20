import React, { useState, useEffect } from 'react';
import { BrowserRouter, Routes, Route, Link, useLocation, useNavigate, useParams } from 'react-router-dom';
import axios from 'axios';
import './App.css';

// Import UI components
import { Button } from './components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from './components/ui/card';
import { Input } from './components/ui/input';
import { Label } from './components/ui/label';
import { Badge } from './components/ui/badge';
import { Separator } from './components/ui/separator';
import { Tabs, TabsContent, TabsList, TabsTrigger } from './components/ui/tabs';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from './components/ui/table';
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle, DialogTrigger } from './components/ui/dialog';
import { Textarea } from './components/ui/textarea';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from './components/ui/select';
import { Checkbox } from './components/ui/checkbox';
import { Progress } from './components/ui/progress';
import { Alert, AlertDescription } from './components/ui/alert';
import { toast, useToast } from './hooks/use-toast';
import { Toaster } from './components/ui/toaster';

// Icons
import { Upload, Users, Mail, BarChart3, Plus, Search, Filter, Edit, Trash2, FileSpreadsheet, Eye, Play, Pause, Settings, ArrowLeft, Send, Clock, TrendingUp, CreditCard, CheckCircle, AlertCircle, Crown } from 'lucide-react';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

// Auth Context
const AuthContext = React.createContext();

const useAuth = () => {
  const context = React.useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within AuthProvider');
  }
  return context;
};

const AuthProvider = ({ children }) => {
  const [user, setUser] = useState(null);
  const [token, setToken] = useState(localStorage.getItem('auth_token') || null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (token) {
      axios.defaults.headers.common['Authorization'] = `Bearer ${token}`;
      checkAuth();
    } else {
      setLoading(false);
    }
  }, [token]);

  const checkAuth = async () => {
    try {
      const response = await axios.get(`${API}/auth/me`);
      setUser(response.data);
    } catch (error) {
      localStorage.removeItem('auth_token');
      setToken(null);
    } finally {
      setLoading(false);
    }
  };

  const login = async (email, password) => {
    try {
      const response = await axios.post(`${API}/auth/login`, { email, password });
      const { access_token, user: userData } = response.data;
      
      setToken(access_token);
      setUser(userData);
      localStorage.setItem('auth_token', access_token);
      axios.defaults.headers.common['Authorization'] = `Bearer ${access_token}`;
      
      return { success: true };
    } catch (error) {
      return { success: false, error: error.response?.data?.detail || 'Login failed' };
    }
  };

  const register = async (userData) => {
    try {
      await axios.post(`${API}/auth/register`, userData);
      return { success: true };
    } catch (error) {
      return { success: false, error: error.response?.data?.detail || 'Registration failed' };
    }
  };

  const logout = () => {
    setToken(null);
    setUser(null);
    localStorage.removeItem('auth_token');
    delete axios.defaults.headers.common['Authorization'];
  };

  const value = { user, token, login, register, logout, loading, checkAuth };
  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
};

// Protected Route Component
const ProtectedRoute = ({ children }) => {
  const { user, token, loading } = useAuth();
  const location = useLocation();

  if (loading) {
    return (
      <div className="flex justify-center items-center min-h-screen">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-500"></div>
      </div>
    );
  }

  if (!token || !user) {
    return <Login />;
  }

  return children;
};

// Login Component
const Login = () => {
  const [isLogin, setIsLogin] = useState(true);
  const [formData, setFormData] = useState({
    email: '',
    password: '',
    full_name: '',
    confirmPassword: ''
  });
  const [errors, setErrors] = useState({});
  const [loading, setLoading] = useState(false);
  const { login, register } = useAuth();
  const { toast } = useToast();
  const navigate = useNavigate();

  const handleChange = (e) => {
    const { name, value } = e.target;
    setFormData(prev => ({ ...prev, [name]: value }));
    if (errors[name]) {
      setErrors(prev => ({ ...prev, [name]: '' }));
    }
  };

  const validateForm = () => {
    const newErrors = {};
    
    if (!formData.email) newErrors.email = 'Email is required';
    else if (!/\S+@\S+\.\S+/.test(formData.email)) newErrors.email = 'Email is invalid';
    
    if (!formData.password) newErrors.password = 'Password is required';
    else if (formData.password.length < 8) newErrors.password = 'Password must be at least 8 characters';
    
    if (!isLogin) {
      if (!formData.full_name) newErrors.full_name = 'Full name is required';
      if (formData.password !== formData.confirmPassword) {
        newErrors.confirmPassword = 'Passwords do not match';
      }
    }
    
    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!validateForm()) return;

    setLoading(true);
    
    try {
      if (isLogin) {
        const result = await login(formData.email, formData.password);
        if (result.success) {
          toast({ title: "Success", description: "Logged in successfully!" });
          navigate('/dashboard');
        } else {
          setErrors({ submit: result.error });
        }
      } else {
        const result = await register({
          email: formData.email,
          password: formData.password,
          full_name: formData.full_name
        });
        if (result.success) {
          toast({ title: "Success", description: "Account created! Please log in." });
          setIsLogin(true);
          setFormData({ email: formData.email, password: '', full_name: '', confirmPassword: '' });
        } else {
          setErrors({ submit: result.error });
        }
      }
    } catch (error) {
      setErrors({ submit: 'An unexpected error occurred' });
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-blue-50 to-indigo-100 py-12 px-4">
      <div className="max-w-md w-full space-y-8 bg-white p-8 rounded-xl shadow-2xl">
        <div className="text-center">
          <Mail className="mx-auto h-12 w-12 text-indigo-600" />
          <h2 className="mt-6 text-3xl font-bold text-gray-900">MailerPro</h2>
          <p className="mt-2 text-sm text-gray-600">
            {isLogin ? 'Sign in to your account' : 'Create your account'}
          </p>
        </div>
        
        <form className="mt-8 space-y-6" onSubmit={handleSubmit}>
          {!isLogin && (
            <div>
              <Label htmlFor="full_name">Full Name</Label>
              <Input
                id="full_name"
                name="full_name"
                type="text"
                value={formData.full_name}
                onChange={handleChange}
                className={errors.full_name ? 'border-red-500' : ''}
              />
              {errors.full_name && <p className="text-red-500 text-sm mt-1">{errors.full_name}</p>}
            </div>
          )}
          
          <div>
            <Label htmlFor="email">Email</Label>
            <Input
              id="email"
              name="email"
              type="email"
              value={formData.email}
              onChange={handleChange}
              className={errors.email ? 'border-red-500' : ''}
            />
            {errors.email && <p className="text-red-500 text-sm mt-1">{errors.email}</p>}
          </div>
          
          <div>
            <Label htmlFor="password">Password</Label>
            <Input
              id="password"
              name="password"
              type="password"
              value={formData.password}
              onChange={handleChange}
              className={errors.password ? 'border-red-500' : ''}
            />
            {errors.password && <p className="text-red-500 text-sm mt-1">{errors.password}</p>}
          </div>
          
          {!isLogin && (
            <div>
              <Label htmlFor="confirmPassword">Confirm Password</Label>
              <Input
                id="confirmPassword"
                name="confirmPassword"
                type="password"
                value={formData.confirmPassword}
                onChange={handleChange}
                className={errors.confirmPassword ? 'border-red-500' : ''}
              />
              {errors.confirmPassword && <p className="text-red-500 text-sm mt-1">{errors.confirmPassword}</p>}
            </div>
          )}

          {errors.submit && (
            <Alert variant="destructive">
              <AlertCircle className="h-4 w-4" />
              <AlertDescription>{errors.submit}</AlertDescription>
            </Alert>
          )}

          <Button type="submit" className="w-full" disabled={loading}>
            {loading ? 'Processing...' : (isLogin ? 'Sign In' : 'Create Account')}
          </Button>
        </form>
        
        <div className="text-center">
          <button
            type="button"
            onClick={() => setIsLogin(!isLogin)}
            className="text-indigo-600 hover:text-indigo-500 text-sm"
          >
            {isLogin ? 'Need an account? Sign up' : 'Already have an account? Sign in'}
          </button>
        </div>
      </div>
    </div>
  );
};

// Dashboard Component
const Dashboard = () => {
  const [stats, setStats] = useState({
    total_contacts: 0,
    total_campaigns: 0,
    recent_contacts: 0,
    active_campaigns: 0,
    total_emails_sent: 0,
    overall_open_rate: 0,
    subscription: {
      plan: 'free',
      plan_name: 'Free Trial',
      status: 'active',
      limits: {
        contacts: { used: 0, limit: 100 },
        campaigns: { used: 0, limit: 2 }
      }
    }
  });

  useEffect(() => {
    fetchStats();
  }, []);

  const fetchStats = async () => {
    try {
      const response = await axios.get(`${API}/stats/dashboard`);
      setStats(response.data);
    } catch (error) {
      console.error('Error fetching stats:', error);
    }
  };

  const getPlanBadge = (plan) => {
    const badges = {
      free: { variant: "secondary", label: "Free", icon: null },
      pro: { variant: "default", label: "Pro", icon: <Crown className="h-3 w-3" /> },
      agency: { variant: "default", label: "Agency", icon: <Crown className="h-3 w-3" /> }
    };
    return badges[plan] || badges.free;
  };

  return (
    <div className="space-y-8">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-3xl font-bold tracking-tight">Dashboard</h2>
          <p className="text-muted-foreground">
            Overview of your email outreach campaigns
          </p>
        </div>
        <div className="flex items-center gap-2">
          {getPlanBadge(stats.subscription.plan).icon}
          <Badge variant={getPlanBadge(stats.subscription.plan).variant}>
            {getPlanBadge(stats.subscription.plan).label} Plan
          </Badge>
        </div>
      </div>

      {/* Subscription Limits */}
      <div className="grid gap-4 md:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle className="text-sm">Contact Usage</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-2">
              <div className="flex justify-between text-sm">
                <span>{stats.subscription.limits.contacts.used} used</span>
                <span>{stats.subscription.limits.contacts.limit} limit</span>
              </div>
              <Progress 
                value={(stats.subscription.limits.contacts.used / stats.subscription.limits.contacts.limit) * 100} 
                className="h-2" 
              />
            </div>
          </CardContent>
        </Card>
        
        <Card>
          <CardHeader>
            <CardTitle className="text-sm">Campaign Usage</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-2">
              <div className="flex justify-between text-sm">
                <span>{stats.subscription.limits.campaigns.used} used</span>
                <span>{stats.subscription.limits.campaigns.limit} limit</span>
              </div>
              <Progress 
                value={(stats.subscription.limits.campaigns.used / stats.subscription.limits.campaigns.limit) * 100} 
                className="h-2" 
              />
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Main Stats */}
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Total Contacts</CardTitle>
            <Users className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{stats.total_contacts}</div>
            <p className="text-xs text-muted-foreground">
              {stats.recent_contacts} added this week
            </p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Total Campaigns</CardTitle>
            <Mail className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{stats.total_campaigns}</div>
            <p className="text-xs text-muted-foreground">
              {stats.active_campaigns} currently active
            </p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Emails Sent</CardTitle>
            <Send className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{stats.total_emails_sent}</div>
            <p className="text-xs text-muted-foreground">
              Across all campaigns
            </p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Open Rate</CardTitle>
            <TrendingUp className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{stats.overall_open_rate}%</div>
            <p className="text-xs text-muted-foreground">
              Overall performance
            </p>
          </CardContent>
        </Card>
      </div>

      {/* Upgrade prompt for free users */}
      {stats.subscription.plan === 'free' && (
        <Card className="border-yellow-200 bg-yellow-50">
          <CardContent className="pt-6">
            <div className="flex items-center gap-4">
              <Crown className="h-8 w-8 text-yellow-600" />
              <div className="flex-1">
                <h3 className="font-semibold text-yellow-800">Upgrade to Pro</h3>
                <p className="text-sm text-yellow-700">
                  Get 5,000 contacts, 20 campaigns, and 1,000 emails/day
                </p>
              </div>
              <Link to="/subscription">
                <Button className="bg-yellow-600 hover:bg-yellow-700">
                  Upgrade Now
                </Button>
              </Link>
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  );
};

// Subscription Component
const Subscription = () => {
  const [plans, setPlans] = useState({});
  const [loading, setLoading] = useState(false);
  const { user, checkAuth } = useAuth();
  const { toast } = useToast();

  useEffect(() => {
    fetchPlans();
  }, []);

  const fetchPlans = async () => {
    try {
      const response = await axios.get(`${API}/subscription/plans`);
      setPlans(response.data.plans);
    } catch (error) {
      console.error('Error fetching plans:', error);
    }
  };

  const handleSubscribe = async (planKey) => {
    if (planKey === 'free') return;
    
    setLoading(true);
    try {
      const response = await axios.post(`${API}/subscription/checkout`, {
        plan: planKey,
        origin_url: window.location.origin
      });
      
      // Redirect to Stripe Checkout
      window.location.href = response.data.url;
      
    } catch (error) {
      toast({
        title: "Error",
        description: error.response?.data?.detail || "Failed to create checkout session",
        variant: "destructive"
      });
    } finally {
      setLoading(false);
    }
  };

  const getPlanColor = (planKey) => {
    const colors = {
      free: "border-gray-200",
      pro: "border-blue-200 ring-2 ring-blue-500",
      agency: "border-purple-200 ring-2 ring-purple-500"
    };
    return colors[planKey] || colors.free;
  };

  return (
    <div className="space-y-8">
      <div className="text-center">
        <h2 className="text-3xl font-bold">Choose Your Plan</h2>
        <p className="text-muted-foreground mt-2">
          Scale your email outreach with the right plan for your needs
        </p>
      </div>

      <div className="grid gap-8 md:grid-cols-3">
        {Object.entries(plans).map(([planKey, plan]) => (
          <Card key={planKey} className={`relative ${getPlanColor(planKey)}`}>
            {planKey === 'pro' && (
              <div className="absolute -top-3 left-1/2 transform -translate-x-1/2">
                <Badge className="bg-blue-500">Most Popular</Badge>
              </div>
            )}
            
            <CardHeader className="text-center pb-2">
              <CardTitle className="text-2xl">{plan.name}</CardTitle>
              <div className="text-4xl font-bold">
                ${plan.price}
                {plan.price > 0 && <span className="text-lg font-normal text-muted-foreground">/month</span>}
              </div>
            </CardHeader>
            
            <CardContent className="space-y-4">
              <div className="space-y-2 text-sm">
                <div className="flex justify-between">
                  <span>Contacts</span>
                  <span className="font-medium">{plan.contacts_limit.toLocaleString()}</span>
                </div>
                <div className="flex justify-between">
                  <span>Campaigns</span>
                  <span className="font-medium">{plan.campaigns_limit}</span>
                </div>
                <div className="flex justify-between">
                  <span>Emails/Day</span>
                  <span className="font-medium">{plan.emails_per_day.toLocaleString()}</span>
                </div>
                <div className="flex justify-between">
                  <span>Inboxes</span>
                  <span className="font-medium">{plan.inboxes_limit}</span>
                </div>
              </div>
              
              <Button 
                className="w-full" 
                onClick={() => handleSubscribe(planKey)}
                disabled={loading || user?.subscription_plan === planKey}
                variant={planKey === 'pro' ? 'default' : 'outline'}
              >
                {user?.subscription_plan === planKey ? (
                  <><CheckCircle className="h-4 w-4 mr-2" /> Current Plan</>
                ) : planKey === 'free' ? (
                  'Free Forever'
                ) : (
                  loading ? 'Processing...' : 'Subscribe'
                )}
              </Button>
            </CardContent>
          </Card>
        ))}
      </div>
    </div>
  );
};

// Subscription Success Component
const SubscriptionSuccess = () => {
  const [loading, setLoading] = useState(true);
  const [status, setStatus] = useState(null);
  const { checkAuth } = useAuth();
  const { toast } = useToast();
  const navigate = useNavigate();
  
  useEffect(() => {
    const urlParams = new URLSearchParams(window.location.search);
    const sessionId = urlParams.get('session_id');
    
    if (sessionId) {
      checkPaymentStatus(sessionId);
    } else {
      navigate('/subscription');
    }
  }, []);

  const checkPaymentStatus = async (sessionId) => {
    try {
      const response = await axios.get(`${API}/subscription/checkout/status/${sessionId}`);
      setStatus(response.data);
      
      if (response.data.payment_status === 'paid') {
        await checkAuth(); // Refresh user data
        toast({
          title: "Success!",
          description: "Your subscription has been activated successfully.",
        });
        setTimeout(() => navigate('/dashboard'), 2000);
      }
    } catch (error) {
      console.error('Error checking payment status:', error);
      toast({
        title: "Error",
        description: "Failed to verify payment status",
        variant: "destructive"
      });
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="text-center space-y-4">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-500 mx-auto"></div>
          <p>Processing your subscription...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="flex items-center justify-center min-h-screen">
      <Card className="max-w-md w-full">
        <CardContent className="pt-6 text-center space-y-4">
          {status?.payment_status === 'paid' ? (
            <>
              <CheckCircle className="h-16 w-16 text-green-500 mx-auto" />
              <h2 className="text-2xl font-bold text-green-700">Payment Successful!</h2>
              <p className="text-muted-foreground">
                Your subscription has been activated. You'll be redirected to the dashboard shortly.
              </p>
            </>
          ) : (
            <>
              <AlertCircle className="h-16 w-16 text-red-500 mx-auto" />
              <h2 className="text-2xl font-bold text-red-700">Payment Failed</h2>
              <p className="text-muted-foreground">
                There was an issue with your payment. Please try again.
              </p>
              <Button onClick={() => navigate('/subscription')}>
                Back to Subscription
              </Button>
            </>
          )}
        </CardContent>
      </Card>
    </div>
  );
};

// Update the existing Contacts component to show limits
const Contacts = () => {
  // ... existing contacts code ...
  const [contacts, setContacts] = useState([]);
  const [loading, setLoading] = useState(true);
  const [searchTerm, setSearchTerm] = useState('');
  const [selectedFile, setSelectedFile] = useState(null);
  const [uploading, setUploading] = useState(false);
  const [showAddDialog, setShowAddDialog] = useState(false);
  const [newContact, setNewContact] = useState({
    first_name: '',
    last_name: '',
    email: '',
    company: '',
    phone: '',
    tags: ''
  });
  const { toast } = useToast();
  const { user } = useAuth();

  useEffect(() => {
    fetchContacts();
  }, []);

  const fetchContacts = async (search = '') => {
    try {
      setLoading(true);
      const params = search ? `?search=${encodeURIComponent(search)}` : '';
      const response = await axios.get(`${API}/contacts${params}`);
      setContacts(response.data);
    } catch (error) {
      console.error('Error fetching contacts:', error);
      if (error.response?.status === 401) {
        // Handle auth error
        return;
      }
      toast({
        title: "Error",
        description: error.response?.data?.detail || "Failed to fetch contacts",
        variant: "destructive"
      });
    } finally {
      setLoading(false);
    }
  };

  // Rest of contacts component logic...
  const handleSearch = (e) => {
    const value = e.target.value;
    setSearchTerm(value);
    
    // Debounce search
    const timeoutId = setTimeout(() => {
      fetchContacts(value);
    }, 300);
    
    return () => clearTimeout(timeoutId);
  };

  const handleAddContact = async () => {
    try {
      const contactData = {
        ...newContact,
        tags: newContact.tags ? newContact.tags.split(',').map(tag => tag.trim()) : []
      };
      
      await axios.post(`${API}/contacts`, contactData);
      
      toast({
        title: "Success",
        description: "Contact added successfully",
      });
      
      setShowAddDialog(false);
      setNewContact({
        first_name: '',
        last_name: '',
        email: '',
        company: '',
        phone: '',
        tags: ''
      });
      
      fetchContacts();
    } catch (error) {
      console.error('Error adding contact:', error);
      toast({
        title: "Error",
        description: error.response?.data?.detail || "Failed to add contact",
        variant: "destructive"
      });
    }
  };

  const handleFileUpload = async () => {
    if (!selectedFile) {
      toast({
        title: "Error",
        description: "Please select a CSV file",
        variant: "destructive"
      });
      return;
    }

    setUploading(true);
    const formData = new FormData();
    formData.append('file', selectedFile);

    try {
      const response = await axios.post(`${API}/contacts/upload-csv`, formData, {
        headers: {
          'Content-Type': 'multipart/form-data',
        },
      });

      const { contacts_created, contacts_skipped, errors } = response.data;
      
      // Show detailed success message
      let description = `${contacts_created} contacts imported successfully`;
      if (contacts_skipped > 0) {
        description += `, ${contacts_skipped} skipped (duplicates)`;
      }
      if (errors && errors.length > 0) {
        description += `, ${errors.length} errors found`;
      }

      toast({
        title: "CSV Import Complete",
        description: description,
      });

      // Show errors if any (first few)
      if (errors && errors.length > 0) {
        console.log('CSV Import Errors:', errors);
        toast({
          title: "Import Warnings",
          description: `Some rows had issues: ${errors.slice(0, 2).join(', ')}${errors.length > 2 ? '...' : ''}`,
          variant: "destructive"
        });
      }

      setSelectedFile(null);
      fetchContacts();
    } catch (error) {
      console.error('Error uploading CSV:', error);
      toast({
        title: "CSV Import Failed",
        description: error.response?.data?.detail || "Failed to upload CSV file. Check file format and try again.",
        variant: "destructive"
      });
    } finally {
      setUploading(false);
    }
  };

  return (
    <div className="space-y-8">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-3xl font-bold tracking-tight">Contacts</h2>
          <p className="text-muted-foreground">
            Manage your contact database
          </p>
        </div>
        <Link to="/subscription">
          <Button variant="outline" size="sm">
            <Crown className="h-4 w-4 mr-2" />
            Upgrade for More
          </Button>
        </Link>
      </div>

      {/* Contact limit warning */}
      {user && (
        <Card className="border-yellow-200 bg-yellow-50">
          <CardContent className="pt-4">
            <div className="flex items-center justify-between">
              <div>
                <h4 className="font-medium text-yellow-800">Contact Usage</h4>
                <p className="text-sm text-yellow-700">
                  You're using {contacts.length} of your contact limit
                </p>
              </div>
              <Badge variant="secondary">
                {user.subscription_plan} Plan
              </Badge>
            </div>
          </CardContent>
        </Card>
      )}

      <div className="flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
        <div className="flex gap-2">
          <div className="relative flex-1 md:max-w-sm">
            <Search className="absolute left-2 top-2.5 h-4 w-4 text-muted-foreground" />
            <Input
              placeholder="Search contacts..."
              value={searchTerm}
              onChange={handleSearch}
              className="pl-8"
            />
          </div>
        </div>

        <div className="flex gap-2">
          <input
            type="file"
            accept=".csv"
            onChange={(e) => setSelectedFile(e.target.files[0])}
            className="hidden"
            id="csv-upload"
          />
          <label htmlFor="csv-upload">
            <Button variant="outline" className="cursor-pointer" asChild>
              <span>
                <FileSpreadsheet className="mr-2 h-4 w-4" />
                Upload CSV
              </span>
            </Button>
          </label>
          
          {selectedFile && (
            <Button onClick={handleFileUpload} disabled={uploading}>
              <Upload className="mr-2 h-4 w-4" />
              {uploading ? 'Uploading...' : 'Import'}
            </Button>
          )}

          <Dialog open={showAddDialog} onOpenChange={setShowAddDialog}>
            <DialogTrigger asChild>
              <Button>
                <Plus className="mr-2 h-4 w-4" />
                Add Contact
              </Button>
            </DialogTrigger>
            <DialogContent className="sm:max-w-[425px]">
              <DialogHeader>
                <DialogTitle>Add New Contact</DialogTitle>
                <DialogDescription>
                  Add a new contact to your database.
                </DialogDescription>
              </DialogHeader>
              <div className="grid gap-4 py-4">
                <div className="grid grid-cols-2 gap-4">
                  <div className="grid gap-2">
                    <Label htmlFor="first_name">First Name</Label>
                    <Input
                      id="first_name"
                      value={newContact.first_name}
                      onChange={(e) => setNewContact({...newContact, first_name: e.target.value})}
                    />
                  </div>
                  <div className="grid gap-2">
                    <Label htmlFor="last_name">Last Name</Label>
                    <Input
                      id="last_name"
                      value={newContact.last_name}
                      onChange={(e) => setNewContact({...newContact, last_name: e.target.value})}
                    />
                  </div>
                </div>
                <div className="grid gap-2">
                  <Label htmlFor="email">Email</Label>
                  <Input
                    id="email"
                    type="email"
                    value={newContact.email}
                    onChange={(e) => setNewContact({...newContact, email: e.target.value})}
                  />
                </div>
                <div className="grid gap-2">
                  <Label htmlFor="company">Company</Label>
                  <Input
                    id="company"
                    value={newContact.company}
                    onChange={(e) => setNewContact({...newContact, company: e.target.value})}
                  />
                </div>
                <div className="grid gap-2">
                  <Label htmlFor="phone">Phone</Label>
                  <Input
                    id="phone"
                    value={newContact.phone}
                    onChange={(e) => setNewContact({...newContact, phone: e.target.value})}
                  />
                </div>
                <div className="grid gap-2">
                  <Label htmlFor="tags">Tags (comma separated)</Label>
                  <Input
                    id="tags"
                    value={newContact.tags}
                    onChange={(e) => setNewContact({...newContact, tags: e.target.value})}
                  />
                </div>
              </div>
              <DialogFooter>
                <Button type="submit" onClick={handleAddContact}>Add Contact</Button>
              </DialogFooter>
            </DialogContent>
          </Dialog>
        </div>
      </div>

      {selectedFile && (
        <Card>
          <CardContent className="pt-6">
            <div className="space-y-3">
              <div className="flex items-center gap-2">
                <FileSpreadsheet className="h-4 w-4" />
                <span className="text-sm font-medium">{selectedFile.name}</span>
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={() => setSelectedFile(null)}
                >
                  <Trash2 className="h-4 w-4" />
                </Button>
              </div>
              <div className="bg-blue-50 p-3 rounded-md border">
                <p className="text-xs text-blue-800 font-medium mb-2">📝 Expected CSV Format:</p>
                <code className="text-xs text-blue-700 block">
                  first_name,last_name,email,company,phone,tags<br/>
                  John,Doe,john@example.com,Acme Corp,555-1234,lead,prospect<br/>
                  Jane,Smith,jane@example.com,Tech Inc,,customer
                </code>
                <p className="text-xs text-blue-700 mt-2">
                  <strong>Required:</strong> first_name, email &nbsp;•&nbsp; 
                  <strong>Optional:</strong> last_name, company, phone, tags
                </p>
              </div>
            </div>
          </CardContent>
        </Card>
      )}

      <Card>
        <CardContent>
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Name</TableHead>
                <TableHead>Email</TableHead>
                <TableHead>Company</TableHead>
                <TableHead>Tags</TableHead>
                <TableHead>Actions</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {loading ? (
                <TableRow>
                  <TableCell colSpan={5} className="text-center py-8">
                    Loading contacts...
                  </TableCell>
                </TableRow>
              ) : contacts.length === 0 ? (
                <TableRow>
                  <TableCell colSpan={5} className="text-center py-8">
                    No contacts found. Upload a CSV or add contacts manually.
                  </TableCell>
                </TableRow>
              ) : (
                contacts.map((contact) => (
                  <TableRow key={contact.id}>
                    <TableCell>
                      {contact.first_name} {contact.last_name}
                    </TableCell>
                    <TableCell>{contact.email}</TableCell>
                    <TableCell>{contact.company || '-'}</TableCell>
                    <TableCell>
                      <div className="flex gap-1 flex-wrap">
                        {contact.tags?.map((tag) => (
                          <Badge key={tag} variant="secondary" className="text-xs">
                            {tag}
                          </Badge>
                        ))}
                      </div>
                    </TableCell>
                    <TableCell>
                      <div className="flex gap-2">
                        <Button variant="ghost" size="sm">
                          <Edit className="h-4 w-4" />
                        </Button>
                        <Button variant="ghost" size="sm">
                          <Trash2 className="h-4 w-4" />
                        </Button>
                      </div>
                    </TableCell>
                  </TableRow>
                ))
              )}
            </TableBody>
          </Table>
        </CardContent>
      </Card>
    </div>
  );
};

// Placeholder for other components (keep existing implementations)
const Campaigns = () => {
  return (
    <div className="space-y-8">
      <div>
        <h2 className="text-3xl font-bold tracking-tight">Campaigns</h2>
        <p className="text-muted-foreground">Create and manage email campaigns</p>
      </div>
      <Card>
        <CardContent className="pt-6">
          <div className="text-center py-8">
            <Mail className="mx-auto h-12 w-12 text-muted-foreground" />
            <h3 className="mt-4 text-lg font-medium">Campaign management coming soon</h3>
            <p className="text-muted-foreground">Create powerful email sequences and campaigns</p>
          </div>
        </CardContent>
      </Card>
    </div>
  );
};

const SMTPConfigs = () => {
  const [smtpConfigs, setSmtpConfigs] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showAddDialog, setShowAddDialog] = useState(false);
  const [showEditDialog, setShowEditDialog] = useState(false);
  const [showTestDialog, setShowTestDialog] = useState(false);
  const [currentConfig, setCurrentConfig] = useState(null);
  const [newConfig, setNewConfig] = useState({
    name: '',
    provider: 'custom',
    email: '',
    smtp_host: '',
    smtp_port: 587,
    smtp_username: '',
    smtp_password: '',
    use_tls: true,
    use_ssl: false,
    daily_limit: 300
  });
  const [testData, setTestData] = useState({
    test_email: '',
    subject: 'Test Email from MailerPro',
    content: 'This is a test email to verify your SMTP configuration.'
  });
  const [testResult, setTestResult] = useState(null);
  const [testLoading, setTestLoading] = useState(false);
  const { toast } = useToast();
  const { user } = useAuth();

  useEffect(() => {
    fetchSMTPConfigs();
  }, []);

  const fetchSMTPConfigs = async () => {
    try {
      setLoading(true);
      const response = await axios.get(`${API}/smtp-configs`);
      setSmtpConfigs(response.data);
    } catch (error) {
      console.error('Error fetching SMTP configs:', error);
      toast({
        title: "Error",
        description: error.response?.data?.detail || "Failed to fetch SMTP configurations",
        variant: "destructive"
      });
    } finally {
      setLoading(false);
    }
  };

  const handleAddConfig = async () => {
    try {
      await axios.post(`${API}/smtp-configs`, newConfig);
      toast({
        title: "Success",
        description: "SMTP configuration added successfully",
      });
      setShowAddDialog(false);
      setNewConfig({
        name: '',
        provider: 'custom',
        email: '',
        smtp_host: '',
        smtp_port: 587,
        smtp_username: '',
        smtp_password: '',
        use_tls: true,
        use_ssl: false,
        daily_limit: 300
      });
      fetchSMTPConfigs();
    } catch (error) {
      console.error('Error adding SMTP config:', error);
      toast({
        title: "Error",
        description: error.response?.data?.detail || "Failed to add SMTP configuration",
        variant: "destructive"
      });
    }
  };

  const handleEditConfig = async () => {
    try {
      await axios.put(`${API}/smtp-configs/${currentConfig.id}`, currentConfig);
      toast({
        title: "Success",
        description: "SMTP configuration updated successfully",
      });
      setShowEditDialog(false);
      setCurrentConfig(null);
      fetchSMTPConfigs();
    } catch (error) {
      console.error('Error updating SMTP config:', error);
      toast({
        title: "Error",
        description: error.response?.data?.detail || "Failed to update SMTP configuration",
        variant: "destructive"
      });
    }
  };

  const handleDeleteConfig = async (configId) => {
    if (!window.confirm('Are you sure you want to delete this SMTP configuration?')) {
      return;
    }

    try {
      await axios.delete(`${API}/smtp-configs/${configId}`);
      toast({
        title: "Success",
        description: "SMTP configuration deleted successfully",
      });
      fetchSMTPConfigs();
    } catch (error) {
      console.error('Error deleting SMTP config:', error);
      toast({
        title: "Error",
        description: error.response?.data?.detail || "Failed to delete SMTP configuration",
        variant: "destructive"
      });
    }
  };

  const handleTestConfig = async () => {
    setTestLoading(true);
    try {
      const response = await axios.post(`${API}/smtp-configs/${currentConfig.id}/test`, testData);
      setTestResult(response.data);
      
      // Show different toast messages based on error type
      if (response.data.success) {
        toast({
          title: "Success!",
          description: "Test email sent successfully. Check your inbox.",
        });
      } else if (response.data.error_type === 'gmail_app_password_required') {
        toast({
          title: "Gmail Setup Required",
          description: "Please use an App Password instead of your regular password.",
          variant: "destructive"
        });
      } else {
        toast({
          title: "Test Failed",
          description: response.data.message,
          variant: "destructive"
        });
      }
    } catch (error) {
      console.error('Error testing SMTP config:', error);
      setTestResult({ success: false, message: error.response?.data?.detail || "Test failed" });
      toast({
        title: "Error",
        description: error.response?.data?.detail || "Failed to test SMTP configuration",
        variant: "destructive"
      });
    } finally {
      setTestLoading(false);
    }
  };

  const getProviderDefaults = (provider) => {
    const defaults = {
      gmail: { smtp_host: 'smtp.gmail.com', smtp_port: 587, use_tls: true, use_ssl: false },
      outlook: { smtp_host: 'smtp-mail.outlook.com', smtp_port: 587, use_tls: true, use_ssl: false },
      custom: { smtp_host: '', smtp_port: 587, use_tls: true, use_ssl: false }
    };
    return defaults[provider] || defaults.custom;
  };

  const handleProviderChange = (provider, isEdit = false) => {
    const defaults = getProviderDefaults(provider);
    if (isEdit) {
      setCurrentConfig({ ...currentConfig, provider, ...defaults });
    } else {
      setNewConfig({ ...newConfig, provider, ...defaults });
    }
  };

  const getStatusBadge = (config) => {
    if (!config.is_active) {
      return <Badge variant="secondary">Inactive</Badge>;
    }
    if (config.is_verified) {
      return <Badge variant="default">Verified</Badge>;
    }
    return <Badge variant="outline">Not Verified</Badge>;
  };

  return (
    <div className="space-y-8">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-3xl font-bold tracking-tight">SMTP Settings</h2>
          <p className="text-muted-foreground">
            Manage your email sending accounts
          </p>
        </div>
        <Button onClick={() => setShowAddDialog(true)}>
          <Plus className="mr-2 h-4 w-4" />
          Add SMTP Account
        </Button>
      </div>

      {/* Subscription limit warning */}
      {user && (
        <Card className="border-blue-200 bg-blue-50">
          <CardContent className="pt-4">
            <div className="flex items-center justify-between">
              <div>
                <h4 className="font-medium text-blue-800">Email Account Usage</h4>
                <p className="text-sm text-blue-700">
                  Add unlimited email accounts on all plans
                </p>
              </div>
              <Badge variant="secondary">
                {smtpConfigs.length} accounts connected
              </Badge>
            </div>
          </CardContent>
        </Card>
      )}

      <Card>
        <CardContent>
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Name</TableHead>
                <TableHead>Provider</TableHead>
                <TableHead>Email</TableHead>
                <TableHead>Status</TableHead>
                <TableHead>Daily Limit</TableHead>
                <TableHead>Actions</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {loading ? (
                <TableRow>
                  <TableCell colSpan={6} className="text-center py-8">
                    Loading SMTP configurations...
                  </TableCell>
                </TableRow>
              ) : smtpConfigs.length === 0 ? (
                <TableRow>
                  <TableCell colSpan={6} className="text-center py-8">
                    No SMTP configurations found. Add your first email account to start sending campaigns.
                  </TableCell>
                </TableRow>
              ) : (
                smtpConfigs.map((config) => (
                  <TableRow key={config.id}>
                    <TableCell className="font-medium">{config.name}</TableCell>
                    <TableCell>
                      <Badge variant="outline" className="capitalize">
                        {config.provider}
                      </Badge>
                    </TableCell>
                    <TableCell>{config.email}</TableCell>
                    <TableCell>{getStatusBadge(config)}</TableCell>
                    <TableCell>{config.daily_limit}/day</TableCell>
                    <TableCell>
                      <div className="flex gap-2">
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => {
                            setCurrentConfig(config);
                            setTestData({ ...testData, test_email: config.email });
                            setShowTestDialog(true);
                          }}
                        >
                          <Play className="h-4 w-4" />
                        </Button>
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => {
                            setCurrentConfig({ ...config });
                            setShowEditDialog(true);
                          }}
                        >
                          <Edit className="h-4 w-4" />
                        </Button>
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => handleDeleteConfig(config.id)}
                        >
                          <Trash2 className="h-4 w-4" />
                        </Button>
                      </div>
                    </TableCell>
                  </TableRow>
                ))
              )}
            </TableBody>
          </Table>
        </CardContent>
      </Card>

      {/* Add SMTP Config Dialog */}
      <Dialog open={showAddDialog} onOpenChange={setShowAddDialog}>
        <DialogContent className="sm:max-w-[600px]">
          <DialogHeader>
            <DialogTitle>Add SMTP Configuration</DialogTitle>
            <DialogDescription>
              Configure a new email account for sending campaigns.
            </DialogDescription>
          </DialogHeader>
          <div className="grid gap-4 py-4">
            <div className="grid gap-2">
              <Label htmlFor="name">Account Name</Label>
              <Input
                id="name"
                placeholder="e.g., My Gmail Account"
                value={newConfig.name}
                onChange={(e) => setNewConfig({...newConfig, name: e.target.value})}
              />
            </div>
            
            <div className="grid gap-2">
              <Label htmlFor="provider">Provider</Label>
              <Select
                value={newConfig.provider}
                onValueChange={(value) => handleProviderChange(value)}
              >
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="gmail">Gmail</SelectItem>
                  <SelectItem value="outlook">Outlook</SelectItem>
                  <SelectItem value="custom">Custom SMTP</SelectItem>
                </SelectContent>
              </Select>
            </div>

            <div className="grid gap-2">
              <Label htmlFor="email">Email Address</Label>
              <Input
                id="email"
                type="email"
                placeholder="your-email@example.com"
                value={newConfig.email}
                onChange={(e) => setNewConfig({...newConfig, email: e.target.value})}
              />
            </div>

            <div className="grid grid-cols-2 gap-4">
              <div className="grid gap-2">
                <Label htmlFor="smtp_host">SMTP Host</Label>
                <Input
                  id="smtp_host"
                  placeholder="smtp.example.com"
                  value={newConfig.smtp_host}
                  onChange={(e) => setNewConfig({...newConfig, smtp_host: e.target.value})}
                />
              </div>
              <div className="grid gap-2">
                <Label htmlFor="smtp_port">SMTP Port</Label>
                <Input
                  id="smtp_port"
                  type="number"
                  placeholder="587"
                  value={newConfig.smtp_port}
                  onChange={(e) => setNewConfig({...newConfig, smtp_port: parseInt(e.target.value) || 587})}
                />
              </div>
            </div>

            <div className="grid gap-2">
              <Label htmlFor="smtp_username">Username</Label>
              <Input
                id="smtp_username"
                placeholder="Usually your email address"
                value={newConfig.smtp_username}
                onChange={(e) => setNewConfig({...newConfig, smtp_username: e.target.value})}
              />
            </div>

            <div className="grid gap-2">
              <Label htmlFor="smtp_password">Password</Label>
              <Input
                id="smtp_password"
                type="password"
                placeholder={newConfig.provider === 'gmail' ? 'Use App Password (not your regular password)' : 'Your email password or app password'}
                value={newConfig.smtp_password}
                onChange={(e) => setNewConfig({...newConfig, smtp_password: e.target.value})}
              />
              {newConfig.provider === 'gmail' && (
                <p className="text-xs text-muted-foreground">
                  📝 Gmail requires an App Password. <a href="https://support.google.com/accounts/answer/185833" target="_blank" rel="noopener noreferrer" className="text-blue-600 hover:underline">Learn how to create one →</a>
                </p>
              )}
              {newConfig.provider === 'outlook' && (
                <p className="text-xs text-muted-foreground">
                  📝 Outlook may require an App Password if 2FA is enabled. <a href="https://support.microsoft.com/en-us/account-billing/manage-app-passwords-for-two-step-verification-d6dc8c6d-4bf7-4b3b-b4fa-c4f476589db9" target="_blank" rel="noopener noreferrer" className="text-blue-600 hover:underline">Learn more →</a>
                </p>
              )}
            </div>

            <div className="grid grid-cols-2 gap-4">
              <div className="flex items-center space-x-2">
                <Checkbox
                  id="use_tls"
                  checked={newConfig.use_tls}
                  onCheckedChange={(checked) => setNewConfig({...newConfig, use_tls: checked})}
                />
                <Label htmlFor="use_tls">Use TLS</Label>
              </div>
              <div className="grid gap-2">
                <Label htmlFor="daily_limit">Daily Limit</Label>
                <Input
                  id="daily_limit"
                  type="number"
                  placeholder="300"
                  value={newConfig.daily_limit}
                  onChange={(e) => setNewConfig({...newConfig, daily_limit: parseInt(e.target.value) || 300})}
                />
              </div>
            </div>
          </div>
          <DialogFooter>
            <Button type="submit" onClick={handleAddConfig}>Add Configuration</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Edit SMTP Config Dialog */}
      <Dialog open={showEditDialog} onOpenChange={setShowEditDialog}>
        <DialogContent className="sm:max-w-[600px]">
          <DialogHeader>
            <DialogTitle>Edit SMTP Configuration</DialogTitle>
            <DialogDescription>
              Update your email account settings.
            </DialogDescription>
          </DialogHeader>
          {currentConfig && (
            <div className="grid gap-4 py-4">
              <div className="grid gap-2">
                <Label htmlFor="edit_name">Account Name</Label>
                <Input
                  id="edit_name"
                  value={currentConfig.name}
                  onChange={(e) => setCurrentConfig({...currentConfig, name: e.target.value})}
                />
              </div>
              
              <div className="grid gap-2">
                <Label htmlFor="edit_provider">Provider</Label>
                <Select
                  value={currentConfig.provider}
                  onValueChange={(value) => handleProviderChange(value, true)}
                >
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="gmail">Gmail</SelectItem>
                    <SelectItem value="outlook">Outlook</SelectItem>
                    <SelectItem value="custom">Custom SMTP</SelectItem>
                  </SelectContent>
                </Select>
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div className="grid gap-2">
                  <Label htmlFor="edit_smtp_host">SMTP Host</Label>
                  <Input
                    id="edit_smtp_host"
                    value={currentConfig.smtp_host}
                    onChange={(e) => setCurrentConfig({...currentConfig, smtp_host: e.target.value})}
                  />
                </div>
                <div className="grid gap-2">
                  <Label htmlFor="edit_smtp_port">SMTP Port</Label>
                  <Input
                    id="edit_smtp_port"
                    type="number"
                    value={currentConfig.smtp_port}
                    onChange={(e) => setCurrentConfig({...currentConfig, smtp_port: parseInt(e.target.value) || 587})}
                  />
                </div>
              </div>

              <div className="grid gap-2">
                <Label htmlFor="edit_daily_limit">Daily Limit</Label>
                <Input
                  id="edit_daily_limit"
                  type="number"
                  value={currentConfig.daily_limit}
                  onChange={(e) => setCurrentConfig({...currentConfig, daily_limit: parseInt(e.target.value) || 300})}
                />
              </div>

              <div className="flex items-center space-x-2">
                <Checkbox
                  id="edit_is_active"
                  checked={currentConfig.is_active}
                  onCheckedChange={(checked) => setCurrentConfig({...currentConfig, is_active: checked})}
                />
                <Label htmlFor="edit_is_active">Account Active</Label>
              </div>
            </div>
          )}
          <DialogFooter>
            <Button type="submit" onClick={handleEditConfig}>Update Configuration</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Test SMTP Config Dialog */}
      <Dialog open={showTestDialog} onOpenChange={setShowTestDialog}>
        <DialogContent className="sm:max-w-[500px]">
          <DialogHeader>
            <DialogTitle>Test SMTP Configuration</DialogTitle>
            <DialogDescription>
              Send a test email to verify your SMTP settings.
            </DialogDescription>
          </DialogHeader>
          <div className="grid gap-4 py-4">
            <div className="grid gap-2">
              <Label htmlFor="test_email">Test Email Address</Label>
              <Input
                id="test_email"
                type="email"
                value={testData.test_email}
                onChange={(e) => setTestData({...testData, test_email: e.target.value})}
              />
            </div>
            
            <div className="grid gap-2">
              <Label htmlFor="test_subject">Subject</Label>
              <Input
                id="test_subject"
                value={testData.subject}
                onChange={(e) => setTestData({...testData, subject: e.target.value})}
              />
            </div>

            <div className="grid gap-2">
              <Label htmlFor="test_content">Message</Label>
              <Textarea
                id="test_content"
                value={testData.content}
                onChange={(e) => setTestData({...testData, content: e.target.value})}
                rows={4}
              />
            </div>

            {testResult && (
              <div className="space-y-3">
                <Alert variant={testResult.success ? "default" : "destructive"}>
                  <AlertCircle className="h-4 w-4" />
                  <AlertDescription>
                    {testResult.message}
                  </AlertDescription>
                </Alert>
                
                {testResult.error_type === 'gmail_app_password_required' && (
                  <Card className="bg-blue-50 border-blue-200">
                    <CardContent className="pt-4 text-sm">
                      <h4 className="font-medium mb-2">Gmail Setup Steps:</h4>
                      <ol className="list-decimal list-inside space-y-1 text-blue-800">
                        <li>Go to your <a href="https://myaccount.google.com/security" target="_blank" rel="noopener noreferrer" className="text-blue-600 hover:underline">Google Account Security</a></li>
                        <li>Enable 2-factor authentication if not already enabled</li>
                        <li>Go to <a href="https://myaccount.google.com/apppasswords" target="_blank" rel="noopener noreferrer" className="text-blue-600 hover:underline">App Passwords</a></li>
                        <li>Generate a new app password for "Mail"</li>
                        <li>Use that 16-character password (not your regular password)</li>
                      </ol>
                    </CardContent>
                  </Card>
                )}
                
                {testResult.error_type === 'authentication_failed' && (
                  <Card className="bg-yellow-50 border-yellow-200">
                    <CardContent className="pt-4 text-sm">
                      <h4 className="font-medium mb-2">Authentication Tips:</h4>
                      <ul className="list-disc list-inside space-y-1 text-yellow-800">
                        <li>Double-check your username and password</li>
                        <li>For Gmail: Use App Password instead of regular password</li>
                        <li>For Outlook: May need App Password if 2FA is enabled</li>
                        <li>Username is usually your full email address</li>
                      </ul>
                    </CardContent>
                  </Card>
                )}
              </div>
            )}
          </div>
          <DialogFooter>
            <Button 
              type="submit" 
              onClick={handleTestConfig}
              disabled={testLoading || !testData.test_email}
            >
              {testLoading ? 'Testing...' : 'Send Test Email'}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
};

// Layout Component
const Layout = ({ children }) => {
  const location = useLocation();
  const { user, logout } = useAuth();

  const navigation = [
    { name: 'Dashboard', href: '/dashboard', icon: BarChart3 },
    { name: 'Contacts', href: '/contacts', icon: Users },
    { name: 'Campaigns', href: '/campaigns', icon: Mail },
    { name: 'SMTP Settings', href: '/smtp', icon: Settings },
    { name: 'Subscription', href: '/subscription', icon: CreditCard },
  ];

  return (
    <div className="min-h-screen bg-background">
      <div className="border-b">
        <div className="flex h-16 items-center px-4">
          <div className="flex items-center space-x-4">
            <Mail className="h-6 w-6" />
            <h1 className="text-xl font-bold">MailerPro</h1>
          </div>
          <nav className="ml-8 flex items-center space-x-4">
            {navigation.map((item) => {
              const isActive = location.pathname === item.href;
              return (
                <Link
                  key={item.name}
                  to={item.href}
                  className={`flex items-center space-x-2 px-3 py-2 text-sm font-medium rounded-md transition-colors ${
                    isActive
                      ? 'bg-primary text-primary-foreground'
                      : 'text-muted-foreground hover:text-foreground hover:bg-muted'
                  }`}
                >
                  <item.icon className="h-4 w-4" />
                  <span>{item.name}</span>
                </Link>
              );
            })}
          </nav>
          <div className="ml-auto flex items-center space-x-4">
            {user && (
              <>
                <div className="flex items-center space-x-2">
                  <Badge variant="outline">{user.subscription_plan}</Badge>
                  <span className="text-sm text-muted-foreground">{user.full_name}</span>
                </div>
                <Button variant="outline" onClick={logout}>
                  Logout
                </Button>
              </>
            )}
          </div>
        </div>
      </div>
      <main className="p-8">
        {children}
      </main>
      <Toaster />
    </div>
  );
};

function App() {
  return (
    <div className="App">
      <BrowserRouter>
        <AuthProvider>
          <Routes>
            <Route path="/login" element={<Login />} />
            <Route path="/subscription/success" element={
              <ProtectedRoute>
                <Layout>
                  <SubscriptionSuccess />
                </Layout>
              </ProtectedRoute>
            } />
            <Route path="/subscription/cancel" element={
              <ProtectedRoute>
                <Layout>
                  <div className="text-center">
                    <h2 className="text-2xl font-bold">Payment Cancelled</h2>
                    <p className="text-muted-foreground">Your payment was cancelled.</p>
                    <Link to="/subscription">
                      <Button className="mt-4">Back to Subscription</Button>
                    </Link>
                  </div>
                </Layout>
              </ProtectedRoute>
            } />
            <Route path="*" element={
              <ProtectedRoute>
                <Layout>
                  <Routes>
                    <Route path="/dashboard" element={<Dashboard />} />
                    <Route path="/contacts" element={<Contacts />} />
                    <Route path="/campaigns" element={<Campaigns />} />
                    <Route path="/smtp" element={<SMTPConfigs />} />
                    <Route path="/subscription" element={<Subscription />} />
                    <Route path="/" element={<Dashboard />} />
                  </Routes>
                </Layout>
              </ProtectedRoute>
            } />
          </Routes>
        </AuthProvider>
      </BrowserRouter>
    </div>
  );
}

export default App;