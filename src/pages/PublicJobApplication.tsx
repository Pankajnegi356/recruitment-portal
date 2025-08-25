import React, { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../components/ui/card';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import { Textarea } from '../components/ui/textarea';
import { Alert, AlertDescription } from '../components/ui/alert';
import { ArrowLeft, MapPin, Clock, Users, DollarSign, Upload } from 'lucide-react';

interface JobDetails {
  id: number;
  title: string;
  description: string;
  department_name: string;
  location: string;
  employment_type: string;
  experience_level: string;
  requirements: string;
  salary_min: number;
  salary_max: number;
}

interface ApplicationData {
  name: string;
  email: string;
  resume_url: string;
}

export default function PublicJobApplication() {
  const { applicationCode } = useParams<{ applicationCode: string }>();
  const navigate = useNavigate();
  
  const [job, setJob] = useState<JobDetails | null>(null);
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);
  
  const [formData, setFormData] = useState<ApplicationData>({
    name: '',
    email: '',
    resume_url: ''
  });

  const [resumeFile, setResumeFile] = useState<File | null>(null);

  useEffect(() => {
    fetchJobDetails();
  }, [applicationCode]);

  const fetchJobDetails = async () => {
    try {
      setLoading(true);
      const response = await fetch(`http://localhost:5000/api/public/apply/${applicationCode}`);
      
      if (!response.ok) {
        if (response.status === 404) {
          setError('Job not found or no longer available');
        } else {
          setError('Failed to load job details');
        }
        return;
      }
      
      const jobData = await response.json();
      setJob(jobData);
      setError(null); // Clear any previous errors
    } catch (err) {
      setError('Failed to load job details');
      console.error('Error fetching job details:', err);
    } finally {
      setLoading(false);
    }
  };

  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement>) => {
    const { name, value } = e.target;
    setFormData(prev => ({
      ...prev,
      [name]: value
    }));
  };

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) {
      // Validate file type
      const allowedTypes = ['application/pdf', 'application/msword', 'application/vnd.openxmlformats-officedocument.wordprocessingml.document'];
      if (!allowedTypes.includes(file.type)) {
        setError('Please upload a PDF or Word document');
        return;
      }
      
      // Validate file size (5MB max)
      if (file.size > 5 * 1024 * 1024) {
        setError('File size must be less than 5MB');
        return;
      }
      
      setResumeFile(file);
      setError(null);
    }
  };

  const uploadResume = async (file: File): Promise<string> => {
    try {
      // Create FormData for file upload
      const formData = new FormData();
      formData.append('resume', file);
      
      // Upload to backend
      const response = await fetch('http://localhost:5000/api/upload/resume', {
        method: 'POST',
        body: formData
      });
      
      if (!response.ok) {
        throw new Error('Upload failed');
      }
      
      const result = await response.json();
      return result.url; // Return the uploaded file URL
    } catch (error) {
      console.error('Resume upload failed:', error);
      throw error;
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setSubmitting(true);
    setError(null);
    setSuccess(null);
    
    try {
      // Validate required fields
      if (!formData.name.trim() || !formData.email.trim()) {
        setError('Name and email are required');
        return;
      }
      
      // No need to upload - send file directly
      
      // Create FormData for file upload
      const submitFormData = new FormData();
      submitFormData.append('name', formData.name.trim());
      submitFormData.append('email', formData.email.trim());
      submitFormData.append('resume_url', formData.resume_url);
      
      if (resumeFile) {
        submitFormData.append('resume', resumeFile);
      }

      const response = await fetch(`http://localhost:5000/api/public/apply/${applicationCode}`, {
        method: 'POST',
        body: submitFormData
      });
      
      const result = await response.json();
      
      if (!response.ok) {
        setError(result.error || 'Failed to submit application');
        return;
      }
      
      setSuccess(`Application submitted successfully for ${result.job_title}!`);
      
      // Clear form
      setFormData({ name: '', email: '', resume_url: '' });
      setResumeFile(null);
      
      // Reset file input
      const fileInput = document.getElementById('resume-upload') as HTMLInputElement;
      if (fileInput) fileInput.value = '';
      
    } catch (err) {
      setError('Failed to submit application');
      console.error('Error submitting application:', err);
    } finally {
      setSubmitting(false);
    }
  };

  const formatSalary = (min: number | null, max: number | null) => {
    if (!min && !max) return 'Competitive';
    if (min && max) return `₹${min.toLocaleString()} - ₹${max.toLocaleString()}`;
    if (min) return `From ₹${min.toLocaleString()}`;
    return `Up to ₹${max?.toLocaleString()}`;
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
      </div>
    );
  }

  if (error && !job) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <Card className="max-w-md w-full">
          <CardContent className="pt-6">
            <Alert>
              <AlertDescription>{error}</AlertDescription>
            </Alert>
            <Button onClick={() => window.close()} className="mt-4 w-full">
              Close
            </Button>
          </CardContent>
        </Card>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <div className="bg-white shadow-sm border-b">
        <div className="max-w-6xl mx-auto px-6 py-4">
          <h1 className="text-2xl font-bold text-gray-900">Apply for Position</h1>
        </div>
      </div>

      <div className="max-w-6xl mx-auto px-6 py-6">
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Job Details - Compact */}
          <div className="lg:col-span-2">
            <Card>
              <CardHeader className="pb-4">
                <CardTitle className="text-xl">{job?.title}</CardTitle>
                <CardDescription className="text-base">
                  {job?.department_name}
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-3">
                <div className="grid grid-cols-2 gap-3 text-sm">
                  <div className="flex items-center text-gray-600">
                    <MapPin className="h-4 w-4 mr-2" />
                    {job?.location || 'Remote'}
                  </div>
                  <div className="flex items-center text-gray-600">
                    <Clock className="h-4 w-4 mr-2" />
                    {job?.employment_type || 'Full-time'}
                  </div>
                  <div className="flex items-center text-gray-600">
                    <Users className="h-4 w-4 mr-2" />
                    {job?.experience_level || 'Mid-level'}
                  </div>
                  <div className="flex items-center text-gray-600">
                    <DollarSign className="h-4 w-4 mr-2" />
                    {formatSalary(job?.salary_min || null, job?.salary_max || null)}
                  </div>
                </div>
                
                {job?.description && (
                  <div>
                    <h3 className="font-medium text-gray-900 mb-2">Job Description</h3>
                    <div className="text-gray-600 text-sm leading-relaxed">
                      {job.description}
                    </div>
                  </div>
                )}
                
                {job?.requirements && (
                  <div>
                    <h3 className="font-medium text-gray-900 mb-2">Requirements</h3>
                    <div className="text-gray-600 text-sm leading-relaxed">
                      {job.requirements}
                    </div>
                  </div>
                )}
              </CardContent>
            </Card>
          </div>

          {/* Application Form - Prominent */}
          <div>
            <Card className="sticky top-6">
              <CardHeader className="pb-4">
                <CardTitle className="text-lg">Submit Your Application</CardTitle>
                <CardDescription className="text-sm">
                  Fill out the form below to apply for this position
                </CardDescription>
              </CardHeader>
              <CardContent>
                {success && (
                  <Alert className="mb-4 border-green-200 bg-green-50">
                    <AlertDescription className="text-green-800 text-sm">
                      {success}
                    </AlertDescription>
                  </Alert>
                )}
                
                {error && (
                  <Alert className="mb-4 border-red-200 bg-red-50">
                    <AlertDescription className="text-red-800 text-sm">
                      {error}
                    </AlertDescription>
                  </Alert>
                )}

                <form onSubmit={handleSubmit} className="space-y-4">
                  <div>
                    <Label htmlFor="name" className="text-sm">Full Name *</Label>
                    <Input
                      id="name"
                      name="name"
                      type="text"
                      required
                      value={formData.name}
                      onChange={handleInputChange}
                      placeholder="Enter your full name"
                      className="mt-1 h-9"
                    />
                  </div>

                  <div>
                    <Label htmlFor="email" className="text-sm">Email Address *</Label>
                    <Input
                      id="email"
                      name="email"
                      type="email"
                      required
                      value={formData.email}
                      onChange={handleInputChange}
                      placeholder="Enter your email address"
                      className="mt-1 h-9"
                    />
                  </div>

                  <div>
                    <Label htmlFor="resume-upload" className="text-sm">Resume Upload</Label>
                    <div className="mt-1">
                      <Input
                        id="resume-upload"
                        type="file"
                        accept=".pdf,.doc,.docx"
                        onChange={handleFileChange}
                        className="cursor-pointer h-9"
                      />
                      <p className="text-xs text-gray-500 mt-1">
                        Upload your resume (PDF or Word document, max 5MB)
                      </p>
                    </div>
                  </div>

                  <div>
                    <Label htmlFor="resume_url" className="text-sm">Resume URL (Optional)</Label>
                    <Input
                      id="resume_url"
                      name="resume_url"
                      type="url"
                      value={formData.resume_url}
                      onChange={handleInputChange}
                      placeholder="Or paste a link to your online resume"
                      className="mt-1 h-9"
                    />
                  </div>

                  <Button 
                    type="submit" 
                    className="w-full h-10 mt-6"
                    disabled={submitting}
                  >
                    {submitting ? (
                      <>
                        <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white mr-2"></div>
                        Submitting Application...
                      </>
                    ) : (
                      <>
                        <Upload className="h-4 w-4 mr-2" />
                        Submit Application
                      </>
                    )}
                  </Button>
                </form>
              </CardContent>
            </Card>
          </div>
        </div>
      </div>
    </div>
  );
}
