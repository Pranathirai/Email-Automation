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

      {/* Create Campaign Dialog */}
      <Dialog open={showCreateDialog} onOpenChange={setShowCreateDialog}>
        <DialogContent className="max-w-4xl max-h-[80vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle>Create New Campaign</DialogTitle>
            <DialogDescription>
              Build a multi-step email sequence with A/B testing and personalization
            </DialogDescription>
          </DialogHeader>
          
          <div className="space-y-6">
            {/* Basic Info */}
            <div className="space-y-4">
              <h3 className="text-lg font-medium">Campaign Details</h3>
              
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <Label htmlFor="campaign_name">Campaign Name</Label>
                  <Input
                    id="campaign_name"
                    placeholder="e.g., Welcome Series"
                    value={newCampaign.name}
                    onChange={(e) => setNewCampaign({...newCampaign, name: e.target.value})}
                  />
                </div>
                <div>
                  <Label htmlFor="campaign_description">Description (Optional)</Label>
                  <Input
                    id="campaign_description"
                    placeholder="Brief description"
                    value={newCampaign.description}
                    onChange={(e) => setNewCampaign({...newCampaign, description: e.target.value})}
                  />
                </div>
              </div>

              {/* Settings */}
              <div className="grid grid-cols-3 gap-4">
                <div>
                  <Label htmlFor="daily_limit">Daily Limit per Inbox</Label>
                  <Input
                    id="daily_limit"
                    type="number"
                    value={newCampaign.daily_limit_per_inbox}
                    onChange={(e) => setNewCampaign({...newCampaign, daily_limit_per_inbox: parseInt(e.target.value) || 200})}
                  />
                </div>
                <div>
                  <Label htmlFor="delay_min">Min Delay (seconds)</Label>
                  <Input
                    id="delay_min"
                    type="number"
                    value={newCampaign.delay_min_seconds}
                    onChange={(e) => setNewCampaign({...newCampaign, delay_min_seconds: parseInt(e.target.value) || 300})}
                  />
                </div>
                <div>
                  <Label htmlFor="delay_max">Max Delay (seconds)</Label>
                  <Input
                    id="delay_max"
                    type="number"
                    value={newCampaign.delay_max_seconds}
                    onChange={(e) => setNewCampaign({...newCampaign, delay_max_seconds: parseInt(e.target.value) || 1800})}
                  />
                </div>
              </div>

              <div className="flex items-center space-x-4">
                <div className="flex items-center space-x-2">
                  <Checkbox
                    id="personalization"
                    checked={newCampaign.personalization_enabled}
                    onCheckedChange={(checked) => setNewCampaign({...newCampaign, personalization_enabled: checked})}
                  />
                  <Label htmlFor="personalization">Enable Personalization</Label>
                </div>
                <div className="flex items-center space-x-2">
                  <Checkbox
                    id="ab_testing"
                    checked={newCampaign.a_b_testing_enabled}
                    onCheckedChange={(checked) => setNewCampaign({...newCampaign, a_b_testing_enabled: checked})}
                  />
                  <Label htmlFor="ab_testing">Enable A/B Testing</Label>
                </div>
              </div>
            </div>

            {/* Contact Selection */}
            <div className="space-y-4">
              <h3 className="text-lg font-medium">Select Contacts ({selectedContacts.length} selected)</h3>
              <div className="max-h-48 overflow-y-auto border rounded p-3">
                {contacts.length === 0 ? (
                  <p className="text-muted-foreground text-center py-4">
                    No contacts available. Add contacts first.
                  </p>
                ) : (
                  contacts.map((contact) => (
                    <div key={contact.id} className="flex items-center space-x-2 py-1">
                      <Checkbox
                        id={`contact_${contact.id}`}
                        checked={selectedContacts.includes(contact.id)}
                        onCheckedChange={(checked) => {
                          if (checked) {
                            setSelectedContacts([...selectedContacts, contact.id]);
                          } else {
                            setSelectedContacts(selectedContacts.filter(id => id !== contact.id));
                          }
                        }}
                      />
                      <Label htmlFor={`contact_${contact.id}`} className="text-sm">
                        {contact.first_name} {contact.last_name} ({contact.email})
                        {contact.company && ` - ${contact.company}`}
                      </Label>
                    </div>
                  ))
                )}
              </div>
            </div>

            {/* SMTP Selection */}
            <div className="space-y-4">
              <h3 className="text-lg font-medium">Select Email Accounts ({selectedSmtpConfigs.length} selected)</h3>
              <div className="max-h-32 overflow-y-auto border rounded p-3">
                {smtpConfigs.length === 0 ? (
                  <p className="text-muted-foreground text-center py-4">
                    No SMTP configurations available. Add email accounts first.
                  </p>
                ) : (
                  smtpConfigs.map((smtp) => (
                    <div key={smtp.id} className="flex items-center space-x-2 py-1">
                      <Checkbox
                        id={`smtp_${smtp.id}`}
                        checked={selectedSmtpConfigs.includes(smtp.id)}
                        onCheckedChange={(checked) => {
                          if (checked) {
                            setSelectedSmtpConfigs([...selectedSmtpConfigs, smtp.id]);
                          } else {
                            setSelectedSmtpConfigs(selectedSmtpConfigs.filter(id => id !== smtp.id));
                          }
                        }}
                      />
                      <Label htmlFor={`smtp_${smtp.id}`} className="text-sm">
                        {smtp.name} ({smtp.email}) - {smtp.provider}
                      </Label>
                    </div>
                  ))
                )}
              </div>
            </div>

            {/* Email Steps */}
            <div className="space-y-4">
              <div className="flex items-center justify-between">
                <h3 className="text-lg font-medium">Email Sequence ({newCampaign.steps.length} steps)</h3>
                <Button variant="outline" size="sm" onClick={addStep}>
                  <Plus className="h-4 w-4 mr-2" />
                  Add Follow-up Step
                </Button>
              </div>

              {newCampaign.steps.map((step, stepIndex) => (
                <Card key={stepIndex} className="border-2">
                  <CardContent className="pt-4">
                    <div className="flex items-center justify-between mb-4">
                      <h4 className="font-medium">
                        {stepIndex === 0 ? 'Initial Email' : `Follow-up ${stepIndex} (${step.delay_days} days later)`}
                      </h4>
                      <div className="flex items-center space-x-2">
                        {stepIndex > 0 && (
                          <div className="flex items-center space-x-2">
                            <Label>Delay (days):</Label>
                            <Input
                              type="number"
                              className="w-20"
                              value={step.delay_days}
                              onChange={(e) => updateStep(stepIndex, 'delay_days', parseInt(e.target.value) || 0)}
                            />
                          </div>
                        )}
                        {newCampaign.steps.length > 1 && (
                          <Button
                            variant="ghost"
                            size="sm"
                            onClick={() => removeStep(stepIndex)}
                          >
                            <Trash2 className="h-4 w-4" />
                          </Button>
                        )}
                      </div>
                    </div>

                    {/* Variations */}
                    <div className="space-y-4">
                      <div className="flex items-center justify-between">
                        <h5 className="font-medium">Email Variations ({step.variations.length})</h5>
                        {newCampaign.a_b_testing_enabled && (
                          <Button
                            variant="outline"
                            size="sm"
                            onClick={() => addVariation(stepIndex)}
                          >
                            <Plus className="h-4 w-4 mr-2" />
                            Add Variation
                          </Button>
                        )}
                      </div>

                      {step.variations.map((variation, variationIndex) => (
                        <div key={variationIndex} className="border rounded p-3 space-y-3">
                          <div className="flex items-center justify-between">
                            <Input
                              placeholder="Variation name"
                              value={variation.name}
                              onChange={(e) => updateVariation(stepIndex, variationIndex, 'name', e.target.value)}
                              className="max-w-xs"
                            />
                            <div className="flex items-center space-x-2">
                              {newCampaign.a_b_testing_enabled && (
                                <>
                                  <Label>Weight:</Label>
                                  <Input
                                    type="number"
                                    className="w-16"
                                    value={variation.weight}
                                    onChange={(e) => updateVariation(stepIndex, variationIndex, 'weight', parseInt(e.target.value) || 50)}
                                  />
                                  <span>%</span>
                                </>
                              )}
                              {step.variations.length > 1 && (
                                <Button
                                  variant="ghost"
                                  size="sm"
                                  onClick={() => removeVariation(stepIndex, variationIndex)}
                                >
                                  <Trash2 className="h-4 w-4" />
                                </Button>
                              )}
                            </div>
                          </div>

                          <div>
                            <Label>Subject Line</Label>
                            <div className="flex space-x-2">
                              <Input
                                placeholder="Email subject with {{variables}}"
                                value={variation.subject}
                                onChange={(e) => updateVariation(stepIndex, variationIndex, 'subject', e.target.value)}
                              />
                              <Select onValueChange={(value) => insertVariable(stepIndex, variationIndex, 'subject', value)}>
                                <SelectTrigger className="w-32">
                                  <SelectValue placeholder="Variable" />
                                </SelectTrigger>
                                <SelectContent>
                                  <SelectItem value="first_name">First Name</SelectItem>
                                  <SelectItem value="last_name">Last Name</SelectItem>
                                  <SelectItem value="company">Company</SelectItem>
                                  <SelectItem value="email">Email</SelectItem>
                                </SelectContent>
                              </Select>
                            </div>
                          </div>

                          <div>
                            <Label>Email Content</Label>
                            <div className="space-y-2">
                              <Textarea
                                placeholder="Email content with {{variables}} for personalization"
                                value={variation.content}
                                onChange={(e) => updateVariation(stepIndex, variationIndex, 'content', e.target.value)}
                                rows={6}
                              />
                              <div className="flex space-x-2">
                                <Select onValueChange={(value) => insertVariable(stepIndex, variationIndex, 'content', value)}>
                                  <SelectTrigger className="w-40">
                                    <SelectValue placeholder="Insert Variable" />
                                  </SelectTrigger>
                                  <SelectContent>
                                    <SelectItem value="first_name">{{first_name}}</SelectItem>
                                    <SelectItem value="last_name">{{last_name}}</SelectItem>
                                    <SelectItem value="full_name">{{full_name}}</SelectItem>
                                    <SelectItem value="company">{{company}}</SelectItem>
                                    <SelectItem value="email">{{email}}</SelectItem>
                                  </SelectContent>
                                </Select>
                                <Button
                                  variant="outline"
                                  size="sm"
                                  onClick={() => {
                                    // Preview functionality would go here
                                    toast({
                                      title: "Preview",
                                      description: "Preview with first available contact",
                                    });
                                  }}
                                >
                                  <Eye className="h-4 w-4 mr-2" />
                                  Preview
                                </Button>
                              </div>
                            </div>
                          </div>
                        </div>
                      ))}
                    </div>
                  </CardContent>
                </Card>
              ))}
            </div>

            {/* Variable Help */}
            <Card className="bg-blue-50 border-blue-200">
              <CardContent className="pt-4">
                <h4 className="font-medium text-blue-800 mb-2">💡 Available Variables</h4>
                <div className="grid grid-cols-2 gap-2 text-sm text-blue-700">
                  <div><code>{{first_name}}</code> - Contact's first name</div>
                  <div><code>{{last_name}}</code> - Contact's last name</div>
                  <div><code>{{full_name}}</code> - Full name</div>
                  <div><code>{{company}}</code> - Company name</div>
                  <div><code>{{email}}</code> - Email address</div>
                  <div><code>{{phone}}</code> - Phone number</div>
                </div>
                <p className="text-xs text-blue-600 mt-2">
                  Example: "Hi {{first_name}}, I noticed {{company}} might benefit from..."
                </p>
              </CardContent>
            </Card>
          </div>

          <DialogFooter className="mt-6">
            <Button variant="outline" onClick={() => setShowCreateDialog(false)}>
              Cancel
            </Button>
            <Button 
              onClick={handleCreateCampaign}
              disabled={!newCampaign.name || selectedContacts.length === 0 || selectedSmtpConfigs.length === 0}
            >
              Create Campaign
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Analytics Dialog */}
      <Dialog open={showAnalyticsDialog} onOpenChange={setShowAnalyticsDialog}>
        <DialogContent className="max-w-3xl">
          <DialogHeader>
            <DialogTitle>Campaign Analytics</DialogTitle>
            <DialogDescription>
              Performance breakdown with A/B testing results
            </DialogDescription>
          </DialogHeader>
          
          {analytics && (
            <div className="space-y-6">
              {/* Overall Stats */}
              <div>
                <h3 className="font-medium mb-3">Overall Performance</h3>
                <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                  <Card>
                    <CardContent className="p-4 text-center">
                      <div className="text-2xl font-bold">{analytics.overall?.total_emails || 0}</div>
                      <div className="text-sm text-muted-foreground">Sent</div>
                    </CardContent>
                  </Card>
                  <Card>
                    <CardContent className="p-4 text-center">
                      <div className="text-2xl font-bold text-green-600">{analytics.overall?.open_rate || 0}%</div>
                      <div className="text-sm text-muted-foreground">Open Rate</div>
                    </CardContent>
                  </Card>
                  <Card>
                    <CardContent className="p-4 text-center">
                      <div className="text-2xl font-bold text-blue-600">{analytics.overall?.click_rate || 0}%</div>
                      <div className="text-sm text-muted-foreground">Click Rate</div>
                    </CardContent>
                  </Card>
                  <Card>
                    <CardContent className="p-4 text-center">
                      <div className="text-2xl font-bold text-purple-600">{analytics.overall?.reply_rate || 0}%</div>
                      <div className="text-sm text-muted-foreground">Reply Rate</div>
                    </CardContent>
                  </Card>
                </div>
              </div>

              {/* A/B Testing Breakdown */}
              {analytics.ab_testing && analytics.ab_testing.length > 0 && (
                <div>
                  <h3 className="font-medium mb-3">A/B Testing Results</h3>
                  <div className="space-y-3">
                    {analytics.ab_testing.map((variation, index) => (
                      <Card key={index}>
                        <CardContent className="p-4">
                          <div className="flex items-center justify-between mb-2">
                            <h4 className="font-medium">{variation.variation_name}</h4>
                            <Badge variant="outline">{variation.sent} sent</Badge>
                          </div>
                          <div className="grid grid-cols-4 gap-4 text-sm">
                            <div>
                              <div className="font-medium text-green-600">{variation.open_rate}%</div>
                              <div className="text-muted-foreground">Open Rate</div>
                            </div>
                            <div>
                              <div className="font-medium text-blue-600">{variation.click_rate}%</div>
                              <div className="text-muted-foreground">Click Rate</div>
                            </div>
                            <div>
                              <div className="font-medium text-purple-600">{variation.reply_rate}%</div>
                              <div className="text-muted-foreground">Reply Rate</div>
                            </div>
                            <div>
                              <div className="font-medium">{variation.delivery_rate}%</div>
                              <div className="text-muted-foreground">Delivery Rate</div>
                            </div>
                          </div>
                        </CardContent>
                      </Card>
                    ))}
                  </div>
                </div>
              )}
            </div>
          )}
        </DialogContent>
      </Dialog>
    </div>
  );
};

// Placeholder for other components (keep existing implementations)
const Campaigns = () => {
  const [campaigns, setCampaigns] = useState([]);
  const [contacts, setContacts] = useState([]);
  const [smtpConfigs, setSmtpConfigs] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showCreateDialog, setShowCreateDialog] = useState(false);
  const [showEditDialog, setShowEditDialog] = useState(false);
  const [showPreviewDialog, setShowPreviewDialog] = useState(false);
  const [showAnalyticsDialog, setShowAnalyticsDialog] = useState(false);
  const [currentCampaign, setCurrentCampaign] = useState(null);
  const [selectedContacts, setSelectedContacts] = useState([]);
  const [selectedSmtpConfigs, setSelectedSmtpConfigs] = useState([]);
  const [availableVariables, setAvailableVariables] = useState([]);
  const [previewData, setPreviewData] = useState(null);
  const [analytics, setAnalytics] = useState(null);
  const [newCampaign, setNewCampaign] = useState({
    name: '',
    description: '',
    steps: [
      {
        sequence_order: 1,
        delay_days: 0,
        variations: [
          {
            name: 'Variation A',
            subject: '',
            content: '',
            weight: 100
          }
        ]
      }
    ],
    daily_limit_per_inbox: 200,
    delay_min_seconds: 300,
    delay_max_seconds: 1800,
    personalization_enabled: true,
    a_b_testing_enabled: false
  });
  const { toast } = useToast();
  const { user } = useAuth();

  useEffect(() => {
    fetchCampaigns();
    fetchContacts();
    fetchSmtpConfigs();
    fetchAvailableVariables();
  }, []);

  const fetchCampaigns = async () => {
    try {
      const response = await axios.get(`${API}/campaigns`);
      setCampaigns(response.data);
    } catch (error) {
      console.error('Error fetching campaigns:', error);
      toast({
        title: "Error",
        description: "Failed to fetch campaigns",
        variant: "destructive"
      });
    }
  };

  const fetchContacts = async () => {
    try {
      const response = await axios.get(`${API}/contacts`);
      setContacts(response.data);
    } catch (error) {
      console.error('Error fetching contacts:', error);
    }
  };

  const fetchSmtpConfigs = async () => {
    try {
      const response = await axios.get(`${API}/smtp-configs`);
      setSmtpConfigs(response.data.filter(config => config.is_active));
    } catch (error) {
      console.error('Error fetching SMTP configs:', error);
    }
  };

  const fetchAvailableVariables = async () => {
    try {
      const response = await axios.get(`${API}/templates/variables`);
      setAvailableVariables(response.data);
    } catch (error) {
      console.error('Error fetching variables:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleCreateCampaign = async () => {
    try {
      const campaignData = {
        ...newCampaign,
        contact_ids: selectedContacts,
        smtp_config_ids: selectedSmtpConfigs
      };
      
      await axios.post(`${API}/campaigns`, campaignData);
      toast({
        title: "Success",
        description: "Campaign created successfully",
      });
      
      setShowCreateDialog(false);
      resetNewCampaign();
      fetchCampaigns();
    } catch (error) {
      console.error('Error creating campaign:', error);
      toast({
        title: "Error",
        description: error.response?.data?.detail || "Failed to create campaign",
        variant: "destructive"
      });
    }
  };

  const resetNewCampaign = () => {
    setNewCampaign({
      name: '',
      description: '',
      steps: [
        {
          sequence_order: 1,
          delay_days: 0,
          variations: [
            {
              name: 'Variation A',
              subject: '',
              content: '',
              weight: 100
            }
          ]
        }
      ],
      daily_limit_per_inbox: 200,
      delay_min_seconds: 300,
      delay_max_seconds: 1800,
      personalization_enabled: true,
      a_b_testing_enabled: false
    });
    setSelectedContacts([]);
    setSelectedSmtpConfigs([]);
  };

  const addStep = () => {
    const newStep = {
      sequence_order: newCampaign.steps.length + 1,
      delay_days: 3, // Default 3 days for follow-up
      variations: [
        {
          name: 'Variation A',
          subject: '',
          content: '',
          weight: 100
        }
      ]
    };
    setNewCampaign({
      ...newCampaign,
      steps: [...newCampaign.steps, newStep]
    });
  };

  const removeStep = (stepIndex) => {
    if (newCampaign.steps.length > 1) {
      const newSteps = newCampaign.steps.filter((_, index) => index !== stepIndex);
      // Reorder sequence numbers
      newSteps.forEach((step, index) => {
        step.sequence_order = index + 1;
      });
      setNewCampaign({
        ...newCampaign,
        steps: newSteps
      });
    }
  };

  const addVariation = (stepIndex) => {
    const newSteps = [...newCampaign.steps];
    const currentVariations = newSteps[stepIndex].variations;
    const newVariation = {
      name: `Variation ${String.fromCharCode(65 + currentVariations.length)}`, // A, B, C, etc.
      subject: '',
      content: '',
      weight: 50
    };
    
    // Adjust weights for equal distribution
    const totalVariations = currentVariations.length + 1;
    const equalWeight = Math.floor(100 / totalVariations);
    
    newSteps[stepIndex].variations = [
      ...currentVariations.map(v => ({ ...v, weight: equalWeight })),
      { ...newVariation, weight: equalWeight }
    ];
    
    setNewCampaign({
      ...newCampaign,
      steps: newSteps
    });
  };

  const removeVariation = (stepIndex, variationIndex) => {
    const newSteps = [...newCampaign.steps];
    if (newSteps[stepIndex].variations.length > 1) {
      newSteps[stepIndex].variations = newSteps[stepIndex].variations.filter(
        (_, index) => index !== variationIndex
      );
      // Redistribute weights equally
      const totalVariations = newSteps[stepIndex].variations.length;
      const equalWeight = Math.floor(100 / totalVariations);
      newSteps[stepIndex].variations.forEach(v => v.weight = equalWeight);
      
      setNewCampaign({
        ...newCampaign,
        steps: newSteps
      });
    }
  };

  const updateStep = (stepIndex, field, value) => {
    const newSteps = [...newCampaign.steps];
    newSteps[stepIndex] = { ...newSteps[stepIndex], [field]: value };
    setNewCampaign({
      ...newCampaign,
      steps: newSteps
    });
  };

  const updateVariation = (stepIndex, variationIndex, field, value) => {
    const newSteps = [...newCampaign.steps];
    newSteps[stepIndex].variations[variationIndex] = {
      ...newSteps[stepIndex].variations[variationIndex],
      [field]: value
    };
    setNewCampaign({
      ...newCampaign,
      steps: newSteps
    });
  };

  const insertVariable = (stepIndex, variationIndex, field, variable) => {
    const currentValue = newCampaign.steps[stepIndex].variations[variationIndex][field];
    const newValue = currentValue + `{{${variable}}}`;
    updateVariation(stepIndex, variationIndex, field, newValue);
  };

  const previewPersonalization = async (template, contactId) => {
    try {
      const response = await axios.post(`${API}/campaigns/preview-demo/preview`, {
        template,
        contact_id: contactId
      });
      return response.data.personalized_content;
    } catch (error) {
      console.error('Error previewing personalization:', error);
      return template;
    }
  };

  const handleStartCampaign = async (campaignId) => {
    try {
      await axios.post(`${API}/campaigns/${campaignId}/start`);
      toast({
        title: "Success",
        description: "Campaign started successfully",
      });
      fetchCampaigns();
    } catch (error) {
      console.error('Error starting campaign:', error);
      toast({
        title: "Error",
        description: error.response?.data?.detail || "Failed to start campaign",
        variant: "destructive"
      });
    }
  };

  const handlePauseCampaign = async (campaignId) => {
    try {
      await axios.post(`${API}/campaigns/${campaignId}/pause`);
      toast({
        title: "Success",
        description: "Campaign paused successfully",
      });
      fetchCampaigns();
    } catch (error) {
      console.error('Error pausing campaign:', error);
      toast({
        title: "Error",
        description: error.response?.data?.detail || "Failed to pause campaign",
        variant: "destructive"
      });
    }
  };

  const fetchAnalytics = async (campaignId) => {
    try {
      const response = await axios.get(`${API}/campaigns/${campaignId}/analytics`);
      setAnalytics(response.data);
      setShowAnalyticsDialog(true);
    } catch (error) {
      console.error('Error fetching analytics:', error);
      toast({
        title: "Error", 
        description: "Failed to fetch campaign analytics",
        variant: "destructive"
      });
    }
  };

  const getStatusBadge = (status) => {
    const badges = {
      draft: { variant: "secondary", label: "Draft", color: "gray" },
      scheduled: { variant: "default", label: "Scheduled", color: "blue" },
      sending: { variant: "default", label: "Sending", color: "green" },
      sent: { variant: "outline", label: "Completed", color: "green" },
      paused: { variant: "destructive", label: "Paused", color: "yellow" }
    };
    return badges[status] || badges.draft;
  };

  if (loading) {
    return (
      <div className="flex justify-center items-center min-h-[400px]">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-500"></div>
      </div>
    );
  }

  return (
    <div className="space-y-8">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-3xl font-bold tracking-tight">Campaigns</h2>
          <p className="text-muted-foreground">
            Create and manage email sequences with A/B testing
          </p>
        </div>
        <Button onClick={() => setShowCreateDialog(true)}>
          <Plus className="mr-2 h-4 w-4" />
          Create Campaign
        </Button>
      </div>

      {/* Campaign Usage Info */}
      {user && (
        <Card className="border-purple-200 bg-purple-50">
          <CardContent className="pt-4">
            <div className="flex items-center justify-between">
              <div>
                <h4 className="font-medium text-purple-800">Campaign Usage</h4>
                <p className="text-sm text-purple-700">
                  Multi-step sequences with unlimited A/B testing variations
                </p>
              </div>
              <Badge variant="secondary">
                {campaigns.length} / {user.subscription_plan === 'free' ? '2' : user.subscription_plan === 'pro' ? '20' : '100'} campaigns
              </Badge>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Campaigns Table */}
      <Card>
        <CardContent>
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Campaign Name</TableHead>
                <TableHead>Status</TableHead>
                <TableHead>Steps</TableHead>
                <TableHead>Contacts</TableHead>
                <TableHead>Performance</TableHead>
                <TableHead>Actions</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {campaigns.length === 0 ? (
                <TableRow>
                  <TableCell colSpan={6} className="text-center py-8">
                    <Mail className="mx-auto h-12 w-12 text-muted-foreground mb-4" />
                    <h3 className="text-lg font-medium mb-2">No campaigns yet</h3>
                    <p className="text-muted-foreground mb-4">
                      Create your first email campaign with A/B testing and personalization
                    </p>
                    <Button onClick={() => setShowCreateDialog(true)}>
                      <Plus className="mr-2 h-4 w-4" />
                      Create Your First Campaign
                    </Button>
                  </TableCell>
                </TableRow>
              ) : (
                campaigns.map((campaign) => (
                  <TableRow key={campaign.id}>
                    <TableCell>
                      <div>
                        <div className="font-medium">{campaign.name}</div>
                        {campaign.description && (
                          <div className="text-sm text-muted-foreground">
                            {campaign.description}
                          </div>
                        )}
                      </div>
                    </TableCell>
                    <TableCell>
                      <Badge variant={getStatusBadge(campaign.status).variant}>
                        {getStatusBadge(campaign.status).label}
                      </Badge>
                    </TableCell>
                    <TableCell>{campaign.steps?.length || 0} steps</TableCell>
                    <TableCell>{campaign.contact_ids?.length || 0} contacts</TableCell>
                    <TableCell>
                      <div className="text-sm">
                        <div>📧 {campaign.total_sent || 0} sent</div>
                        <div>📈 {campaign.total_opened || 0} opened</div>
                      </div>
                    </TableCell>
                    <TableCell>
                      <div className="flex gap-2">
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => fetchAnalytics(campaign.id)}
                        >
                          <BarChart3 className="h-4 w-4" />
                        </Button>
                        {campaign.status === 'draft' || campaign.status === 'paused' ? (
                          <Button
                            variant="ghost"
                            size="sm"
                            onClick={() => handleStartCampaign(campaign.id)}
                          >
                            <Play className="h-4 w-4" />
                          </Button>
                        ) : campaign.status === 'sending' ? (
                          <Button
                            variant="ghost"
                            size="sm"
                            onClick={() => handlePauseCampaign(campaign.id)}
                          >
                            <Pause className="h-4 w-4" />
                          </Button>
                        ) : null}
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