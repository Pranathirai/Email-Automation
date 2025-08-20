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
import { toast, useToast } from './hooks/use-toast';
import { Toaster } from './components/ui/toaster';

// Icons
import { Upload, Users, Mail, BarChart3, Plus, Search, Filter, Edit, Trash2, FileSpreadsheet, Eye, Play, Pause, Settings, ArrowLeft, Send, Clock, TrendingUp } from 'lucide-react';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

// Dashboard Component
const Dashboard = () => {
  const [stats, setStats] = useState({
    total_contacts: 0,
    total_campaigns: 0,
    recent_contacts: 0,
    active_campaigns: 0,
    total_emails_sent: 0,
    overall_open_rate: 0
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

  return (
    <div className="space-y-8">
      <div>
        <h2 className="text-3xl font-bold tracking-tight">Dashboard</h2>
        <p className="text-muted-foreground">
          Overview of your email outreach campaigns
        </p>
      </div>

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
    </div>
  );
};

// Contacts Component
const Contacts = () => {
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
      toast({
        title: "Error",
        description: "Failed to fetch contacts",
        variant: "destructive"
      });
    } finally {
      setLoading(false);
    }
  };

  const handleSearch = (e) => {
    const value = e.target.value;
    setSearchTerm(value);
    
    // Debounce search
    const timeoutId = setTimeout(() => {
      fetchContacts(value);
    }, 300);
    
    return () => clearTimeout(timeoutId);
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

      toast({
        title: "Success",
        description: `${response.data.contacts_created} contacts added successfully`,
      });

      setSelectedFile(null);
      fetchContacts();
    } catch (error) {
      console.error('Error uploading CSV:', error);
      toast({
        title: "Error",
        description: error.response?.data?.detail || "Failed to upload CSV",
        variant: "destructive"
      });
    } finally {
      setUploading(false);
    }
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

  return (
    <div className="space-y-8">
      <div>
        <h2 className="text-3xl font-bold tracking-tight">Contacts</h2>
        <p className="text-muted-foreground">
          Manage your contact database
        </p>
      </div>

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
            <div className="flex items-center gap-2">
              <FileSpreadsheet className="h-4 w-4" />
              <span className="text-sm">{selectedFile.name}</span>
              <Button
                variant="ghost"
                size="sm"
                onClick={() => setSelectedFile(null)}
              >
                <Trash2 className="h-4 w-4" />
              </Button>
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

// Campaign List Component
const Campaigns = () => {
  const [campaigns, setCampaigns] = useState([]);
  const [loading, setLoading] = useState(true);
  const navigate = useNavigate();
  const { toast } = useToast();

  useEffect(() => {
    fetchCampaigns();
  }, []);

  const fetchCampaigns = async () => {
    try {
      setLoading(true);
      const response = await axios.get(`${API}/campaigns`);
      setCampaigns(response.data);
    } catch (error) {
      console.error('Error fetching campaigns:', error);
      toast({
        title: "Error",
        description: "Failed to fetch campaigns",
        variant: "destructive"
      });
    } finally {
      setLoading(false);
    }
  };

  const handleSendCampaign = async (campaignId) => {
    try {
      const response = await axios.post(`${API}/campaigns/${campaignId}/send`);
      
      if (response.data.success) {
        toast({
          title: "Success",
          description: `Campaign scheduled! ${response.data.emails_scheduled} emails will be sent.`,
        });
        fetchCampaigns();
      } else {
        toast({
          title: "Error",
          description: response.data.error || "Failed to send campaign",
          variant: "destructive"
        });
      }
    } catch (error) {
      console.error('Error sending campaign:', error);
      toast({
        title: "Error",
        description: error.response?.data?.detail || "Failed to send campaign",
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

  const handleResumeCampaign = async (campaignId) => {
    try {
      await axios.post(`${API}/campaigns/${campaignId}/resume`);
      toast({
        title: "Success",
        description: "Campaign resumed successfully",
      });
      fetchCampaigns();
    } catch (error) {
      console.error('Error resuming campaign:', error);
      toast({
        title: "Error",
        description: error.response?.data?.detail || "Failed to resume campaign",
        variant: "destructive"
      });
    }
  };

  const getStatusBadge = (status) => {
    const statusConfig = {
      draft: { variant: "secondary", label: "Draft" },
      scheduled: { variant: "default", label: "Scheduled" },
      sending: { variant: "default", label: "Sending" },
      sent: { variant: "outline", label: "Sent" },
      paused: { variant: "secondary", label: "Paused" }
    };
    
    const config = statusConfig[status] || statusConfig.draft;
    return <Badge variant={config.variant}>{config.label}</Badge>;
  };

  return (
    <div className="space-y-8">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-3xl font-bold tracking-tight">Campaigns</h2>
          <p className="text-muted-foreground">
            Create and manage email campaigns
          </p>
        </div>
        <Button onClick={() => navigate('/campaigns/new')}>
          <Plus className="mr-2 h-4 w-4" />
          New Campaign
        </Button>
      </div>

      <Card>
        <CardContent>
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Name</TableHead>
                <TableHead>Status</TableHead>
                <TableHead>Contacts</TableHead>
                <TableHead>Created</TableHead>
                <TableHead>Actions</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {loading ? (
                <TableRow>
                  <TableCell colSpan={5} className="text-center py-8">
                    Loading campaigns...
                  </TableCell>
                </TableRow>
              ) : campaigns.length === 0 ? (
                <TableRow>
                  <TableCell colSpan={5} className="text-center py-8">
                    <div className="flex flex-col items-center gap-2">
                      <Mail className="h-8 w-8 text-muted-foreground" />
                      <p className="text-lg font-medium">No campaigns yet</p>
                      <p className="text-muted-foreground">Create your first email campaign to get started</p>
                      <Button className="mt-2" onClick={() => navigate('/campaigns/new')}>
                        <Plus className="mr-2 h-4 w-4" />
                        Create Campaign
                      </Button>
                    </div>
                  </TableCell>
                </TableRow>
              ) : (
                campaigns.map((campaign) => (
                  <TableRow key={campaign.id}>
                    <TableCell>
                      <div>
                        <p className="font-medium">{campaign.name}</p>
                        <p className="text-sm text-muted-foreground">{campaign.subject}</p>
                      </div>
                    </TableCell>
                    <TableCell>{getStatusBadge(campaign.status)}</TableCell>
                    <TableCell>{campaign.contact_ids?.length || 0}</TableCell>
                    <TableCell>{new Date(campaign.created_at).toLocaleDateString()}</TableCell>
                    <TableCell>
                      <div className="flex gap-2">
                        {campaign.status === 'draft' && (
                          <Button variant="outline" size="sm" onClick={() => handleSendCampaign(campaign.id)}>
                            <Play className="h-4 w-4" />
                          </Button>
                        )}
                        {campaign.status === 'scheduled' && (
                          <Button variant="outline" size="sm" onClick={() => handlePauseCampaign(campaign.id)}>
                            <Pause className="h-4 w-4" />
                          </Button>
                        )}
                        {campaign.status === 'paused' && (
                          <Button variant="outline" size="sm" onClick={() => handleResumeCampaign(campaign.id)}>
                            <Play className="h-4 w-4" />
                          </Button>
                        )}
                        <Button variant="ghost" size="sm" onClick={() => navigate(`/campaigns/${campaign.id}`)}>
                          <Eye className="h-4 w-4" />
                        </Button>
                        <Button variant="ghost" size="sm" onClick={() => navigate(`/campaigns/${campaign.id}/edit`)}>
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

// SMTP Configuration Component
const SMTPConfigs = () => {
  const [configs, setConfigs] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showAddDialog, setShowAddDialog] = useState(false);
  const [testingConfig, setTestingConfig] = useState(null);
  const [testEmail, setTestEmail] = useState('');
  const [newConfig, setNewConfig] = useState({
    name: '',
    provider: 'custom',
    smtp_host: '',
    smtp_port: 587,
    username: '',
    password: '',
    daily_limit: 100,
    use_tls: true
  });
  const { toast } = useToast();

  useEffect(() => {
    fetchConfigs();
  }, []);

  const fetchConfigs = async () => {
    try {
      setLoading(true);
      const response = await axios.get(`${API}/smtp-configs`);
      setConfigs(response.data);
    } catch (error) {
      console.error('Error fetching SMTP configs:', error);
      toast({
        title: "Error",
        description: "Failed to fetch SMTP configurations",
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
        smtp_host: '',
        smtp_port: 587,
        username: '',
        password: '',
        daily_limit: 100,
        use_tls: true
      });
      
      fetchConfigs();
    } catch (error) {
      console.error('Error adding SMTP config:', error);
      toast({
        title: "Error",
        description: error.response?.data?.detail || "Failed to add SMTP configuration",
        variant: "destructive"
      });
    }
  };

  const handleTestConfig = async (configId) => {
    if (!testEmail) {
      toast({
        title: "Error",
        description: "Please enter a test email address",
        variant: "destructive"
      });
      return;
    }

    setTestingConfig(configId);
    try {
      const response = await axios.post(`${API}/smtp-configs/${configId}/test?test_email=${encodeURIComponent(testEmail)}`);
      
      if (response.data.success) {
        toast({
          title: "Success",
          description: "Test email sent successfully!",
        });
      } else {
        toast({
          title: "Error",
          description: response.data.error || "Failed to send test email",
          variant: "destructive"
        });
      }
    } catch (error) {
      console.error('Error testing SMTP config:', error);
      toast({
        title: "Error",
        description: error.response?.data?.detail || "Failed to test SMTP configuration",
        variant: "destructive"
      });
    } finally {
      setTestingConfig(null);
    }
  };

  const getProviderBadge = (provider) => {
    const providerConfig = {
      gmail: { variant: "default", label: "Gmail OAuth", color: "bg-red-100 text-red-800" },
      outlook: { variant: "default", label: "Outlook OAuth", color: "bg-blue-100 text-blue-800" },
      custom: { variant: "secondary", label: "Custom SMTP", color: "bg-gray-100 text-gray-800" }
    };
    
    const config = providerConfig[provider] || providerConfig.custom;
    return <Badge variant={config.variant} className={config.color}>{config.label}</Badge>;
  };

  return (
    <div className="space-y-8">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-3xl font-bold tracking-tight">SMTP Configurations</h2>
          <p className="text-muted-foreground">
            Manage your email sending accounts
          </p>
        </div>
        <Dialog open={showAddDialog} onOpenChange={setShowAddDialog}>
          <DialogTrigger asChild>
            <Button>
              <Plus className="mr-2 h-4 w-4" />
              Add SMTP Config
            </Button>
          </DialogTrigger>
          <DialogContent className="sm:max-w-[500px]">
            <DialogHeader>
              <DialogTitle>Add SMTP Configuration</DialogTitle>
              <DialogDescription>
                Configure an email account for sending campaigns.
              </DialogDescription>
            </DialogHeader>
            <div className="grid gap-4 py-4">
              <div className="grid gap-2">
                <Label htmlFor="config_name">Configuration Name</Label>
                <Input
                  id="config_name"
                  value={newConfig.name}
                  onChange={(e) => setNewConfig({...newConfig, name: e.target.value})}
                  placeholder="e.g., My Gmail Account"
                />
              </div>
              <div className="grid gap-2">
                <Label htmlFor="provider">Provider</Label>
                <Select value={newConfig.provider} onValueChange={(value) => setNewConfig({...newConfig, provider: value})}>
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="gmail">Gmail OAuth (Coming Soon)</SelectItem>
                    <SelectItem value="outlook">Outlook OAuth (Coming Soon)</SelectItem>
                    <SelectItem value="custom">Custom SMTP</SelectItem>
                  </SelectContent>
                </Select>
              </div>
              {newConfig.provider === 'custom' && (
                <>
                  <div className="grid gap-2">
                    <Label htmlFor="smtp_host">SMTP Host</Label>
                    <Input
                      id="smtp_host"
                      value={newConfig.smtp_host}
                      onChange={(e) => setNewConfig({...newConfig, smtp_host: e.target.value})}
                      placeholder="e.g., smtp.gmail.com"
                    />
                  </div>
                  <div className="grid gap-2">
                    <Label htmlFor="smtp_port">SMTP Port</Label>
                    <Input
                      id="smtp_port"
                      type="number"
                      value={newConfig.smtp_port}
                      onChange={(e) => setNewConfig({...newConfig, smtp_port: parseInt(e.target.value) || 587})}
                    />
                  </div>
                  <div className="grid gap-2">
                    <Label htmlFor="username">Username/Email</Label>
                    <Input
                      id="username"
                      value={newConfig.username}
                      onChange={(e) => setNewConfig({...newConfig, username: e.target.value})}
                      placeholder="your-email@domain.com"
                    />
                  </div>
                  <div className="grid gap-2">
                    <Label htmlFor="password">Password/App Password</Label>
                    <Input
                      id="password"
                      type="password"
                      value={newConfig.password}
                      onChange={(e) => setNewConfig({...newConfig, password: e.target.value})}
                      placeholder="Your email password"
                    />
                  </div>
                </>
              )}
              <div className="grid gap-2">
                <Label htmlFor="daily_limit">Daily Sending Limit</Label>
                <Input
                  id="daily_limit"
                  type="number"
                  value={newConfig.daily_limit}
                  onChange={(e) => setNewConfig({...newConfig, daily_limit: parseInt(e.target.value) || 100})}
                />
              </div>
            </div>
            <DialogFooter>
              <Button type="submit" onClick={handleAddConfig}>Add Configuration</Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>
      </div>

      <Card>
        <CardContent>
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Name</TableHead>
                <TableHead>Provider</TableHead>
                <TableHead>Username</TableHead>
                <TableHead>Daily Limit</TableHead>
                <TableHead>Status</TableHead>
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
              ) : configs.length === 0 ? (
                <TableRow>
                  <TableCell colSpan={6} className="text-center py-8">
                    <div className="flex flex-col items-center gap-2">
                      <Settings className="h-8 w-8 text-muted-foreground" />
                      <p className="text-lg font-medium">No SMTP configurations</p>
                      <p className="text-muted-foreground">Add an email account to start sending campaigns</p>
                      <Button className="mt-2" onClick={() => setShowAddDialog(true)}>
                        <Plus className="mr-2 h-4 w-4" />
                        Add SMTP Config
                      </Button>
                    </div>
                  </TableCell>
                </TableRow>
              ) : (
                configs.map((config) => (
                  <TableRow key={config.id}>
                    <TableCell className="font-medium">{config.name}</TableCell>
                    <TableCell>{getProviderBadge(config.provider)}</TableCell>
                    <TableCell>{config.username}</TableCell>
                    <TableCell>{config.daily_limit}/day</TableCell>
                    <TableCell>
                      <Badge variant={config.is_active ? "default" : "secondary"}>
                        {config.is_active ? "Active" : "Inactive"}
                      </Badge>
                    </TableCell>
                    <TableCell>
                      <div className="flex gap-2">
                        <Input
                          placeholder="test@example.com"
                          value={testEmail}
                          onChange={(e) => setTestEmail(e.target.value)}
                          className="w-40"
                        />
                        <Button 
                          variant="outline" 
                          size="sm"
                          onClick={() => handleTestConfig(config.id)}
                          disabled={testingConfig === config.id}
                        >
                          {testingConfig === config.id ? 'Testing...' : 'Test'}
                        </Button>
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

      <Card>
        <CardHeader>
          <CardTitle>SMTP Provider Recommendations</CardTitle>
          <CardDescription>
            Best email providers for cold outreach deliverability in 2025
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="grid gap-4 md:grid-cols-2">
            <div className="border rounded-lg p-4">
              <h4 className="font-semibold mb-2">🚀 ColdSend.pro (Recommended)</h4>
              <p className="text-sm text-muted-foreground mb-2">
                No warm-up required. 100 high-deliverability inboxes.
              </p>
              <p className="text-xs">$50/month • 10,000 emails • Immediate deployment</p>
            </div>
            <div className="border rounded-lg p-4">
              <h4 className="font-semibold mb-2">📧 SendGrid</h4>
              <p className="text-sm text-muted-foreground mb-2">
                Robust infrastructure with flexible APIs.
              </p>
              <p className="text-xs">$19.95/month • 50,000 emails • Advanced analytics</p>
            </div>
            <div className="border rounded-lg p-4">
              <h4 className="font-semibold mb-2">🎯 Mailgun</h4>
              <p className="text-sm text-muted-foreground mb-2">
                Developer-friendly with email validation.
              </p>
              <p className="text-xs">$15/month • 10,000 emails • Real-time analytics</p>
            </div>
            <div className="border rounded-lg p-4">
              <h4 className="font-semibold mb-2">☁️ Amazon SES</h4>
              <p className="text-sm text-muted-foreground mb-2">
                Cost-effective for AWS users.
              </p>
              <p className="text-xs">$0.10 per 1,000 emails • High scalability</p>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  );
};

// Campaign Form Component
const CampaignForm = ({ isEdit = false }) => {
  const { id } = useParams();
  const navigate = useNavigate();
  const { toast } = useToast();
  const [loading, setLoading] = useState(isEdit);
  const [saving, setSaving] = useState(false);
  const [sending, setSending] = useState(false);
  const [contacts, setContacts] = useState([]);
  const [selectedContacts, setSelectedContacts] = useState([]);
  const [campaign, setCampaign] = useState({
    name: '',
    description: '',
    subject: '',
    content: '',
    daily_limit: 50,
    delay_between_emails: 300,
    personalization_enabled: true
  });

  useEffect(() => {
    fetchContacts();
    if (isEdit && id) {
      fetchCampaign();
    }
  }, [isEdit, id]);

  const fetchContacts = async () => {
    try {
      const response = await axios.get(`${API}/contacts`);
      setContacts(response.data);
    } catch (error) {
      console.error('Error fetching contacts:', error);
    }
  };

  const fetchCampaign = async () => {
    try {
      const response = await axios.get(`${API}/campaigns/${id}`);
      const campaignData = response.data;
      setCampaign(campaignData);
      setSelectedContacts(campaignData.contact_ids || []);
    } catch (error) {
      console.error('Error fetching campaign:', error);
      toast({
        title: "Error",
        description: "Failed to fetch campaign",
        variant: "destructive"
      });
    } finally {
      setLoading(false);
    }
  };

  const handleSaveAndSend = async () => {
    setSaving(true);
    try {
      const campaignData = {
        ...campaign,
        contact_ids: selectedContacts
      };

      const response = await axios.post(`${API}/campaigns`, campaignData);
      const campaignId = response.data.id;

      // Send the campaign immediately
      await handleSendCampaign(campaignId);
      
    } catch (error) {
      console.error('Error creating and sending campaign:', error);
      toast({
        title: "Error",
        description: error.response?.data?.detail || "Failed to create and send campaign",
        variant: "destructive"
      });
    } finally {
      setSaving(false);
    }
  };

  const handleSendCampaign = async (campaignId = id) => {
    setSending(true);
    try {
      const response = await axios.post(`${API}/campaigns/${campaignId}/send`);
      
      if (response.data.success) {
        toast({
          title: "Success",
          description: `Campaign scheduled! ${response.data.emails_scheduled} emails will be sent.`,
        });
        navigate('/campaigns');
      } else {
        toast({
          title: "Error",
          description: response.data.error || "Failed to send campaign",
          variant: "destructive"
        });
      }
    } catch (error) {
      console.error('Error sending campaign:', error);
      toast({
        title: "Error",
        description: error.response?.data?.detail || "Failed to send campaign",
        variant: "destructive"
      });
    } finally {
      setSending(false);
    }
  };

  const handleSave = async () => {
    if (!campaign.name || !campaign.subject || !campaign.content) {
      toast({
        title: "Error",
        description: "Please fill in all required fields",
        variant: "destructive"
      });
      return;
    }

    setSaving(true);
    try {
      const campaignData = {
        ...campaign,
        contact_ids: selectedContacts
      };

      if (isEdit) {
        await axios.put(`${API}/campaigns/${id}`, campaignData);
        toast({
          title: "Success",
          description: "Campaign updated successfully"
        });
      } else {
        await axios.post(`${API}/campaigns`, campaignData);
        toast({
          title: "Success", 
          description: "Campaign created successfully"
        });
      }
      
      navigate('/campaigns');
    } catch (error) {
      console.error('Error saving campaign:', error);
      toast({
        title: "Error",
        description: error.response?.data?.detail || "Failed to save campaign",
        variant: "destructive"
      });
    } finally {
      setSaving(false);
    }
  };

  const handleContactToggle = (contactId) => {
    setSelectedContacts(prev => 
      prev.includes(contactId) 
        ? prev.filter(id => id !== contactId)
        : [...prev, contactId]
    );
  };

  const insertPersonalizationTag = (tag) => {
    const textarea = document.getElementById('campaign-content');
    const cursorPos = textarea.selectionStart;
    const textBefore = campaign.content.substring(0, cursorPos);
    const textAfter = campaign.content.substring(textarea.selectionEnd);
    
    setCampaign({
      ...campaign,
      content: textBefore + tag + textAfter
    });
    
    // Set cursor position after tag
    setTimeout(() => {
      textarea.selectionStart = textarea.selectionEnd = cursorPos + tag.length;
      textarea.focus();
    }, 10);
  };

  if (loading) {
    return (
      <div className="space-y-8">
        <div className="flex items-center gap-4">
          <Button variant="ghost" onClick={() => navigate('/campaigns')}>
            <ArrowLeft className="h-4 w-4" />
          </Button>
          <div>
            <h2 className="text-3xl font-bold tracking-tight">Loading...</h2>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-8">
      <div className="flex items-center gap-4">
        <Button variant="ghost" onClick={() => navigate('/campaigns')}>
          <ArrowLeft className="h-4 w-4" />
        </Button>
        <div>
          <h2 className="text-3xl font-bold tracking-tight">
            {isEdit ? 'Edit Campaign' : 'New Campaign'}
          </h2>
          <p className="text-muted-foreground">
            Create personalized email campaigns for your contacts
          </p>
        </div>
      </div>

      <div className="grid gap-8 md:grid-cols-3">
        <div className="md:col-span-2 space-y-6">
          <Card>
            <CardHeader>
              <CardTitle>Campaign Details</CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="grid gap-2">
                <Label htmlFor="name">Campaign Name *</Label>
                <Input
                  id="name"
                  value={campaign.name}
                  onChange={(e) => setCampaign({...campaign, name: e.target.value})}
                  placeholder="e.g., Product Launch Outreach"
                />
              </div>
              <div className="grid gap-2">
                <Label htmlFor="description">Description</Label>
                <Textarea
                  id="description"
                  value={campaign.description}
                  onChange={(e) => setCampaign({...campaign, description: e.target.value})}
                  placeholder="Brief description of this campaign..."
                  rows={2}
                />
              </div>
              <div className="grid gap-2">
                <Label htmlFor="subject">Email Subject *</Label>
                <Input
                  id="subject"
                  value={campaign.subject}
                  onChange={(e) => setCampaign({...campaign, subject: e.target.value})}
                  placeholder="e.g., Quick question about {{company}}"
                />
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>Email Content</CardTitle>
              <CardDescription>
                Use personalization tags to customize emails for each contact
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="flex gap-2 flex-wrap">
                {[
                  '{{first_name}}',
                  '{{last_name}}', 
                  '{{full_name}}',
                  '{{company}}',
                  '{{email}}'
                ].map(tag => (
                  <Button
                    key={tag}
                    variant="outline"
                    size="sm"
                    onClick={() => insertPersonalizationTag(tag)}
                    type="button"
                  >
                    {tag}
                  </Button>
                ))}
              </div>
              <div className="grid gap-2">
                <Label htmlFor="campaign-content">Email Content *</Label>
                <Textarea
                  id="campaign-content"
                  value={campaign.content}
                  onChange={(e) => setCampaign({...campaign, content: e.target.value})}
                  placeholder="Hi {{first_name}},&#10;&#10;I hope this email finds you well..."
                  rows={12}
                  className="font-mono text-sm"
                />
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>Sending Settings</CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="grid gap-2">
                <Label htmlFor="daily_limit">Daily Sending Limit</Label>
                <Input
                  id="daily_limit"
                  type="number"
                  min="1"
                  max="1000"
                  value={campaign.daily_limit}
                  onChange={(e) => setCampaign({...campaign, daily_limit: parseInt(e.target.value) || 50})}
                />
              </div>
              <div className="grid gap-2">
                <Label htmlFor="delay">Delay Between Emails (seconds)</Label>
                <Input
                  id="delay"
                  type="number"
                  min="60"
                  max="3600"
                  value={campaign.delay_between_emails}
                  onChange={(e) => setCampaign({...campaign, delay_between_emails: parseInt(e.target.value) || 300})}
                />
              </div>
              <div className="flex items-center space-x-2">
                <Checkbox
                  id="personalization"
                  checked={campaign.personalization_enabled}
                  onCheckedChange={(checked) => setCampaign({...campaign, personalization_enabled: checked})}
                />
                <Label htmlFor="personalization">Enable personalization tags</Label>
              </div>
            </CardContent>
          </Card>
        </div>

        <div className="space-y-6">
          <Card>
            <CardHeader>
              <CardTitle>Select Contacts</CardTitle>
              <CardDescription>
                Choose who will receive this campaign
              </CardDescription>
            </CardHeader>
            <CardContent>
              <div className="space-y-2 max-h-96 overflow-y-auto">
                {contacts.map((contact) => (
                  <div key={contact.id} className="flex items-center space-x-2">
                    <Checkbox
                      id={contact.id}
                      checked={selectedContacts.includes(contact.id)}
                      onCheckedChange={() => handleContactToggle(contact.id)}
                    />
                    <Label htmlFor={contact.id} className="flex-1 cursor-pointer">
                      <div className="text-sm">
                        <p className="font-medium">{contact.first_name} {contact.last_name}</p>
                        <p className="text-muted-foreground">{contact.email}</p>
                        {contact.company && (
                          <p className="text-xs text-muted-foreground">{contact.company}</p>
                        )}
                      </div>
                    </Label>
                  </div>
                ))}
              </div>
              {selectedContacts.length > 0 && (
                <div className="mt-4 p-3 bg-muted rounded-md">
                  <p className="text-sm font-medium">
                    {selectedContacts.length} contact{selectedContacts.length > 1 ? 's' : ''} selected
                  </p>
                </div>
              )}
            </CardContent>
          </Card>

          <div className="flex gap-2">
            <Button onClick={handleSave} disabled={saving} className="flex-1">
              {saving ? 'Saving...' : (isEdit ? 'Update Campaign' : 'Create Campaign')}
            </Button>
            {!isEdit && (
              <Button onClick={handleSaveAndSend} disabled={saving} variant="default">
                {saving ? 'Saving...' : 'Create & Send'}
              </Button>
            )}
            {isEdit && campaign.status === 'draft' && (
              <Button onClick={handleSendCampaign} disabled={sending} variant="default">
                {sending ? 'Sending...' : 'Send Now'}
              </Button>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};

// Layout Component
const Layout = ({ children }) => {
  const location = useLocation();

  const navigation = [
    { name: 'Dashboard', href: '/', icon: BarChart3 },
    { name: 'Contacts', href: '/contacts', icon: Users },
    { name: 'Campaigns', href: '/campaigns', icon: Mail },
    { name: 'SMTP Settings', href: '/smtp', icon: Settings },
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
        <Layout>
          <Routes>
            <Route path="/" element={<Dashboard />} />
            <Route path="/contacts" element={<Contacts />} />
            <Route path="/campaigns" element={<Campaigns />} />
            <Route path="/campaigns/new" element={<CampaignForm />} />
            <Route path="/campaigns/:id/edit" element={<CampaignForm isEdit={true} />} />
            <Route path="/smtp" element={<SMTPConfigs />} />
          </Routes>
        </Layout>
      </BrowserRouter>
    </div>
  );
}

export default App;