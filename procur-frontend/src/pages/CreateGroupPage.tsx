import React, { useState } from 'react';
import {
  Box,
  Paper,
  TextField,
  Button,
  Typography,
  Container,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  Chip,
  Alert,
  CircularProgress,
  Card,
  CardContent,
  CardHeader,
  IconButton,
} from '@mui/material';
import Grid from '@mui/material/GridLegacy';
import {
  Group as GroupIcon,
  Add as AddIcon,
  Delete as DeleteIcon,
  Save as SaveIcon,
  ArrowBack as ArrowBackIcon,
} from '@mui/icons-material';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import apiService from '../services/api';
import { CreateGroupRequest } from '../types';

const CreateGroupPage: React.FC = () => {
  const navigate = useNavigate();
  const { user } = useAuth();
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [errors, setErrors] = useState<Record<string, string>>({});

  const [formData, setFormData] = useState<CreateGroupRequest>({
    name: '',
    description: '',
    category: '',
    industry: '',
    privacy: 'public',
    max_members: 50,
    tags: [],
    location: '',
  });

  const [newTag, setNewTag] = useState('');

  const categories = [
    'Technology',
    'Healthcare',
    'Manufacturing',
    'Retail',
    'Finance',
    'Education',
    'Construction',
    'Transportation',
    'Energy',
    'Food & Beverage',
    'Other',
  ];

  const industries = [
    'Software Development',
    'Medical Devices',
    'Automotive',
    'E-commerce',
    'Banking',
    'Higher Education',
    'Commercial Construction',
    'Logistics',
    'Renewable Energy',
    'Restaurant & Hospitality',
    'Other',
  ];

  const handleChange = (field: keyof CreateGroupRequest) => (
    event: React.ChangeEvent<HTMLInputElement> | { target: { value: unknown } }
  ) => {
    const value = event.target.value;
    setFormData(prev => ({ ...prev, [field]: value }));
    
    // Clear error when user starts typing
    if (errors[field]) {
      setErrors(prev => ({ ...prev, [field]: '' }));
    }
  };





  const addTag = () => {
    if (newTag.trim() && !formData.tags.includes(newTag.trim())) {
      setFormData(prev => ({
        ...prev,
        tags: [...prev.tags, newTag.trim()]
      }));
      setNewTag('');
    }
  };

  const removeTag = (tag: string) => {
    setFormData(prev => ({
      ...prev,
      tags: prev.tags.filter(t => t !== tag)
    }));
  };

  const validateForm = () => {
    const newErrors: Record<string, string> = {};

    if (!formData.name.trim()) {
      newErrors.name = 'Group name is required';
    } else if (formData.name.length < 3) {
      newErrors.name = 'Group name must be at least 3 characters';
    }

    if (!formData.description.trim()) {
      newErrors.description = 'Description is required';
    } else if (formData.description.length < 10) {
      newErrors.description = 'Description must be at least 10 characters';
    }

    if (!formData.category) {
      newErrors.category = 'Category is required';
    }

    if (!formData.industry) {
      newErrors.industry = 'Industry is required';
    }

    if (formData.max_members < 2 || formData.max_members > 1000) {
      newErrors.max_members = 'Maximum members must be between 2 and 1000';
    }

    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    
    if (!validateForm()) {
      return;
    }

    setIsSubmitting(true);

    try {
      const group = await apiService.createGroup(formData);
      navigate(`/groups/${group.id}`);
    } catch (error: any) {
      console.error('Failed to create group:', error);
      setErrors({ submit: error.message || 'Failed to create group' });
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleKeyPress = (event: React.KeyboardEvent, action: () => void) => {
    if (event.key === 'Enter') {
      event.preventDefault();
      action();
    }
  };

  return (
    <Container maxWidth="lg" sx={{ py: 4 }}>
      {/* Header */}
      <Box sx={{ mb: 4 }}>
        <Box display="flex" alignItems="center" mb={2}>
          <IconButton 
            onClick={() => navigate(-1)} 
            sx={{ mr: 2 }}
            color="primary"
          >
            <ArrowBackIcon />
          </IconButton>
          <Typography variant="h4" component="h1" sx={{ fontWeight: 'bold' }}>
            Create New Group
          </Typography>
        </Box>
        <Typography variant="body1" color="text.secondary">
          Set up a new procurement group to collaborate with other professionals in your industry.
        </Typography>
      </Box>

      {/* Error Alert */}
      {errors.submit && (
        <Alert severity="error" sx={{ mb: 3 }}>
          {errors.submit}
        </Alert>
      )}

      <Paper sx={{ p: 4 }}>
        <Box component="form" onSubmit={handleSubmit}>
          {/* Basic Information */}
          <Card sx={{ mb: 4 }}>
            <CardHeader
              title="Basic Information"
              titleTypographyProps={{ variant: 'h6', fontWeight: 'bold' }}
              avatar={<GroupIcon color="primary" />}
            />
            <CardContent>
              <Grid container spacing={3}>
                <Grid item xs={12}>
                  <TextField
                    required
                    fullWidth
                    label="Group Name"
                    name="name"
                    value={formData.name}
                    onChange={handleChange('name')}
                    error={!!errors.name}
                    helperText={errors.name || 'Choose a descriptive name for your group'}
                    disabled={isSubmitting}
                  />
                </Grid>

                <Grid item xs={12}>
                  <TextField
                    required
                    fullWidth
                    multiline
                    rows={3}
                    label="Description"
                    name="description"
                    value={formData.description}
                    onChange={handleChange('description')}
                    error={!!errors.description}
                    helperText={errors.description || 'Describe the purpose and goals of this group'}
                    disabled={isSubmitting}
                  />
                </Grid>

                <Grid item xs={12} sm={6}>
                  <FormControl fullWidth required error={!!errors.category}>
                    <InputLabel>Category</InputLabel>
                    <Select
                      value={formData.category}
                      label="Category"
                      onChange={handleChange('category')}
                      disabled={isSubmitting}
                    >
                      {categories.map((category) => (
                        <MenuItem key={category} value={category}>
                          {category}
                        </MenuItem>
                      ))}
                    </Select>
                  </FormControl>
                </Grid>

                <Grid item xs={12} sm={6}>
                  <FormControl fullWidth required error={!!errors.industry}>
                    <InputLabel>Industry</InputLabel>
                    <Select
                      value={formData.industry}
                      label="Industry"
                      onChange={handleChange('industry')}
                      disabled={isSubmitting}
                    >
                      {industries.map((industry) => (
                        <MenuItem key={industry} value={industry}>
                          {industry}
                        </MenuItem>
                      ))}
                    </Select>
                  </FormControl>
                </Grid>

                <Grid item xs={12} sm={6}>
                  <TextField
                    fullWidth
                    label="Location"
                    name="location"
                    value={formData.location}
                    onChange={handleChange('location')}
                    placeholder="e.g., San Francisco, CA"
                    disabled={isSubmitting}
                  />
                </Grid>

                <Grid item xs={12} sm={6}>
                  <TextField
                    fullWidth
                    type="number"
                    label="Maximum Members"
                    name="max_members"
                    value={formData.max_members}
                    onChange={handleChange('max_members')}
                    error={!!errors.max_members}
                    helperText={errors.max_members || 'Maximum number of members allowed'}
                    inputProps={{ min: 2, max: 1000 }}
                    disabled={isSubmitting}
                  />
                </Grid>
              </Grid>
            </CardContent>
          </Card>

          {/* Group Settings */}
          <Card sx={{ mb: 4 }}>
            <CardHeader
              title="Group Settings"
              titleTypographyProps={{ variant: 'h6', fontWeight: 'bold' }}
            />
            <CardContent>
              <Grid container spacing={3}>
                <Grid item xs={12} sm={6}>
                  <FormControl fullWidth required>
                    <InputLabel>Privacy</InputLabel>
                    <Select
                      value={formData.privacy}
                      label="Privacy"
                      onChange={handleChange('privacy')}
                      disabled={isSubmitting}
                    >
                      <MenuItem value="public">Public - Anyone can find and join</MenuItem>
                      <MenuItem value="private">Private - Hidden from search</MenuItem>
                      <MenuItem value="invite_only">Invite Only - Requires invitation</MenuItem>
                    </Select>
                  </FormControl>
                </Grid>
              </Grid>
            </CardContent>
          </Card>





          {/* Tags */}
          <Card sx={{ mb: 4 }}>
            <CardHeader
              title="Tags"
              titleTypographyProps={{ variant: 'h6', fontWeight: 'bold' }}
            />
            <CardContent>
              <Grid container spacing={2}>
                <Grid item xs={12}>
                  <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
                    Add tags to help others find your group
                  </Typography>
                </Grid>
                
                <Grid item xs={12} sm={8}>
                  <TextField
                    fullWidth
                    label="Add Tag"
                    value={newTag}
                    onChange={(e) => setNewTag(e.target.value)}
                    onKeyPress={(e) => handleKeyPress(e, addTag)}
                    placeholder="e.g., procurement, technology, startup"
                    disabled={isSubmitting}
                  />
                </Grid>
                
                <Grid item xs={12} sm={4}>
                  <Button
                    fullWidth
                    variant="outlined"
                    onClick={addTag}
                    disabled={!newTag.trim() || isSubmitting}
                    startIcon={<AddIcon />}
                  >
                    Add
                  </Button>
                </Grid>

                {formData.tags.length > 0 && (
                  <Grid item xs={12}>
                    <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 1 }}>
                      {formData.tags.map((tag, index) => (
                        <Chip
                          key={index}
                          label={tag}
                          onDelete={() => removeTag(tag)}
                          color="secondary"
                          variant="outlined"
                          deleteIcon={<DeleteIcon />}
                        />
                      ))}
                    </Box>
                  </Grid>
                )}
              </Grid>
            </CardContent>
          </Card>

          {/* Submit Button */}
          <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <Button
              variant="outlined"
              onClick={() => navigate(-1)}
              disabled={isSubmitting}
            >
              Cancel
            </Button>
            
            <Button
              type="submit"
              variant="contained"
              size="large"
              disabled={isSubmitting}
              startIcon={isSubmitting ? <CircularProgress size={20} /> : <SaveIcon />}
              sx={{
                px: 4,
                py: 1.5,
                fontSize: '1.1rem',
                fontWeight: 'bold',
                background: 'linear-gradient(45deg, #1976d2, #42a5f5)',
                '&:hover': {
                  background: 'linear-gradient(45deg, #1565c0, #1976d2)',
                },
              }}
            >
              {isSubmitting ? 'Creating Group...' : 'Create Group'}
            </Button>
          </Box>
        </Box>
      </Paper>
    </Container>
  );
};

export default CreateGroupPage;
