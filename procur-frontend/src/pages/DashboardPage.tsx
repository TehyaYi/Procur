import React, { useState, useEffect } from 'react';
import {
  Box,
  Container,
  Paper,
  Typography,
  Card,
  CardContent,
  CardActions,
  Button,
  Chip,
  Avatar,
  List,
  ListItem,
  ListItemText,
  ListItemAvatar,
  Divider,
  CircularProgress,
  Alert,
  IconButton,
  Tooltip,
} from '@mui/material';
import Grid from '@mui/material/GridLegacy';
import {
  Group as GroupIcon,
  Person as PersonIcon,
  Email as EmailIcon,
  TrendingUp as TrendingUpIcon,
  Add as AddIcon,
  Search as SearchIcon,
  Notifications as NotificationsIcon,
  Settings as SettingsIcon,
} from '@mui/icons-material';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import apiService from '../services/api';
import { Group, Invitation } from '../types';

const DashboardPage: React.FC = () => {
  const navigate = useNavigate();
  const { user } = useAuth();
  const [groups, setGroups] = useState<Group[]>([]);
  const [invitations, setInvitations] = useState<Invitation[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchDashboardData = async () => {
      try {
        setLoading(true);
        const [groupsResponse, invitationsResponse] = await Promise.all([
          apiService.getGroups(1, 5), // Get first 5 groups
          apiService.getInvitations(),
        ]);
        
        setGroups(groupsResponse.data);
        setInvitations(invitationsResponse.filter(inv => inv.status === 'pending'));
      } catch (err: any) {
        setError(err.message || 'Failed to load dashboard data');
      } finally {
        setLoading(false);
      }
    };

    fetchDashboardData();
  }, []);

  const getGreeting = () => {
    const hour = new Date().getHours();
    if (hour < 12) return 'Good morning';
    if (hour < 18) return 'Good afternoon';
    return 'Good evening';
  };

  if (loading) {
    return (
      <Box display="flex" justifyContent="center" alignItems="center" minHeight="60vh">
        <CircularProgress />
      </Box>
    );
  }

  return (
    <Container maxWidth="xl" sx={{ mt: 3, mb: 3 }}>
      {/* Header */}
      <Box sx={{ mb: 4 }}>
        <Typography variant="h4" component="h1" gutterBottom sx={{ fontWeight: 'bold' }}>
          {getGreeting()}, {user?.display_name}!
        </Typography>
        <Typography variant="body1" color="text.secondary">
          Welcome back to your procurement dashboard
        </Typography>
      </Box>

      {error && (
        <Alert severity="error" sx={{ mb: 3 }}>
          {error}
        </Alert>
      )}

      {/* Quick Stats */}
      <Grid item container spacing={3} sx={{ mb: 4 }}>
        <Grid item xs={12} sm={6} md={3}>
          <Card sx={{ height: '100%' }}>
            <CardContent>
              <Box display="flex" alignItems="center" justifyContent="space-between">
                <Box>
                  <Typography color="textSecondary" gutterBottom variant="body2">
                    My Groups
                  </Typography>
                  <Typography variant="h4" component="div">
                    {groups.length}
                  </Typography>
                </Box>
                <Avatar sx={{ bgcolor: 'primary.main' }}>
                  <GroupIcon />
                </Avatar>
              </Box>
            </CardContent>
          </Card>
        </Grid>

        <Grid item xs={12} sm={6} md={3}>
          <Card sx={{ height: '100%' }}>
            <CardContent>
              <Box display="flex" alignItems="center" justifyContent="space-between">
                <Box>
                  <Typography color="textSecondary" gutterBottom variant="body2">
                    Pending Invitations
                  </Typography>
                  <Typography variant="h4" component="div">
                    {invitations.length}
                  </Typography>
                </Box>
                <Avatar sx={{ bgcolor: 'warning.main' }}>
                  <EmailIcon />
                </Avatar>
              </Box>
            </CardContent>
          </Card>
        </Grid>

        <Grid item xs={12} sm={6} md={3}>
          <Card sx={{ height: '100%' }}>
            <CardContent>
              <Box display="flex" alignItems="center" justifyContent="space-between">
                <Box>
                  <Typography color="textSecondary" gutterBottom variant="body2">
                    Total Members
                  </Typography>
                  <Typography variant="h4" component="div">
                    {groups.reduce((acc, group) => acc + group.current_members, 0)}
                  </Typography>
                </Box>
                <Avatar sx={{ bgcolor: 'success.main' }}>
                  <PersonIcon />
                </Avatar>
              </Box>
            </CardContent>
          </Card>
        </Grid>

        <Grid item xs={12} sm={6} md={3}>
          <Card sx={{ height: '100%' }}>
            <CardContent>
              <Box display="flex" alignItems="center" justifyContent="space-between">
                <Box>
                  <Typography color="textSecondary" gutterBottom variant="body2">
                    Active Groups
                  </Typography>
                  <Typography variant="h4" component="div">
                    {groups.filter(g => g.is_active).length}
                  </Typography>
                </Box>
                <Avatar sx={{ bgcolor: 'info.main' }}>
                  <TrendingUpIcon />
                </Avatar>
              </Box>
            </CardContent>
          </Card>
        </Grid>
      </Grid>

      {/* Main Content */}
      <Grid item container spacing={3}>
        {/* My Groups */}
        <Grid item xs={12} lg={8}>
          <Paper sx={{ p: 3 }}>
            <Box display="flex" justifyContent="space-between" alignItems="center" mb={3}>
              <Typography variant="h6" component="h2">
                My Groups
              </Typography>
              <Button
                variant="contained"
                startIcon={<AddIcon />}
                onClick={() => navigate('/create-group')}
                sx={{
                  background: 'linear-gradient(45deg, #1976d2, #42a5f5)',
                  '&:hover': {
                    background: 'linear-gradient(45deg, #1565c0, #1976d2)',
                  },
                }}
              >
                Create Group
              </Button>
            </Box>

            {groups.length === 0 ? (
              <Box textAlign="center" py={4}>
                <GroupIcon sx={{ fontSize: 64, color: 'text.secondary', mb: 2 }} />
                <Typography variant="h6" color="text.secondary" gutterBottom>
                  No groups yet
                </Typography>
                <Typography variant="body2" color="text.secondary" mb={3}>
                  Start by creating your first purchasing group or joining an existing one.
                </Typography>
                <Button 
                  variant="outlined" 
                  startIcon={<AddIcon />}
                  onClick={() => navigate('/create-group')}
                >
                  Create Your First Group
                </Button>
              </Box>
            ) : (
              <Grid item container spacing={2}>
                {groups.map((group) => (
                  <Grid item xs={12} sm={6} key={group.id}>
                    <Card variant="outlined" sx={{ height: '100%' }}>
                      <CardContent>
                        <Typography variant="h6" component="h3" gutterBottom>
                          {group.name}
                        </Typography>
                        <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
                          {group.description}
                        </Typography>
                        <Box display="flex" justifyContent="space-between" alignItems="center" mb={2}>
                          <Chip
                            label={group.privacy}
                            size="small"
                            color={group.privacy === 'public' ? 'success' : 'warning'}
                          />
                          <Typography variant="body2" color="text.secondary">
                            {group.current_members}/{group.max_members} members
                          </Typography>
                        </Box>
                        <Typography variant="caption" color="text.secondary">
                          {group.industry} • {group.location}
                        </Typography>
                      </CardContent>
                      <CardActions>
                        <Button size="small" color="primary">
                          View Details
                        </Button>
                        <Button size="small" color="secondary">
                          Manage
                        </Button>
                      </CardActions>
                    </Card>
                  </Grid>
                ))}
              </Grid>
            )}
          </Paper>
        </Grid>

        {/* Sidebar */}
        <Grid item xs={12} lg={4}>
          <Grid item container spacing={3}>
            {/* Pending Invitations */}
            <Grid item xs={12}>
              <Paper sx={{ p: 3 }}>
                <Typography variant="h6" component="h3" gutterBottom>
                  Pending Invitations
                </Typography>
                {invitations.length === 0 ? (
                  <Typography variant="body2" color="text.secondary">
                    No pending invitations
                  </Typography>
                ) : (
                  <List dense>
                    {invitations.slice(0, 3).map((invitation) => (
                      <React.Fragment key={invitation.id}>
                        <ListItem>
                          <ListItemAvatar>
                            <Avatar>
                              <GroupIcon />
                            </Avatar>
                          </ListItemAvatar>
                          <ListItemText
                            primary={invitation.group_name}
                            secondary={`Invited by ${invitation.invited_by_name}`}
                          />
                          <Box>
                            <Button size="small" color="primary" sx={{ mr: 1 }}>
                              Accept
                            </Button>
                            <Button size="small" color="error">
                              Decline
                            </Button>
                          </Box>
                        </ListItem>
                        <Divider />
                      </React.Fragment>
                    ))}
                  </List>
                )}
              </Paper>
            </Grid>

            {/* Quick Actions */}
            <Grid item xs={12}>
              <Paper sx={{ p: 3 }}>
                <Typography variant="h6" component="h3" gutterBottom>
                  Quick Actions
                </Typography>
                <Box display="flex" flexDirection="column" gap={2}>
                  <Button
                    variant="outlined"
                    startIcon={<SearchIcon />}
                    fullWidth
                    sx={{ justifyContent: 'flex-start' }}
                  >
                    Find Groups
                  </Button>
                  <Button
                    variant="outlined"
                    startIcon={<AddIcon />}
                    fullWidth
                    onClick={() => navigate('/create-group')}
                    sx={{ justifyContent: 'flex-start' }}
                  >
                    Create Group
                  </Button>
                  <Button
                    variant="outlined"
                    startIcon={<EmailIcon />}
                    fullWidth
                    sx={{ justifyContent: 'flex-start' }}
                  >
                    Send Invitations
                  </Button>
                  <Button
                    variant="outlined"
                    startIcon={<SettingsIcon />}
                    fullWidth
                    sx={{ justifyContent: 'flex-start' }}
                  >
                    Account Settings
                  </Button>
                </Box>
              </Paper>
            </Grid>

            {/* Recent Activity */}
            <Grid item xs={12}>
              <Paper sx={{ p: 3 }}>
                <Typography variant="h6" component="h3" gutterBottom>
                  Recent Activity
                </Typography>
                <List dense>
                  <ListItem>
                    <ListItemText
                      primary="Joined Tech Procurement Group"
                      secondary="2 hours ago"
                    />
                  </ListItem>
                  <Divider />
                  <ListItem>
                    <ListItemText
                      primary="Invitation sent to john@company.com"
                      secondary="1 day ago"
                    />
                  </ListItem>
                  <Divider />
                  <ListItem>
                    <ListItemText
                      primary="Created Healthcare Supplies Group"
                      secondary="3 days ago"
                    />
                  </ListItem>
                </List>
              </Paper>
            </Grid>
          </Grid>
        </Grid>
      </Grid>
    </Container>
  );
};

export default DashboardPage;
