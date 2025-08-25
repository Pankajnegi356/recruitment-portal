import { useState, useEffect } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { createCandidate, updateCandidate, submitCandidateResume, getDepartments, getJobs } from "../../services/api.js";

interface CandidateFormProps {
  candidate?: any;
  onSubmit: (candidate: any) => void;
  onCancel: () => void;
}

export default function CandidateForm({ candidate, onSubmit, onCancel }: CandidateFormProps) {
  const [formData, setFormData] = useState({
    name: "",
    email: "",
    phone: "",
    position_applied: "",
    department_id: "",
    job_id: "",
    experience_years: "",
    current_salary: "",
    expected_salary: "",
    source: "direct"
  });
  
  const [resumeFile, setResumeFile] = useState(null);
  
  const [departments, setDepartments] = useState([]);
  const [jobs, setJobs] = useState([]);
  const [loading, setLoading] = useState(false);
  const [errors, setErrors] = useState({});

  useEffect(() => {
    const fetchData = async () => {
      try {
        const [deptData, jobData] = await Promise.all([
          getDepartments(),
          getJobs()
        ]);
        setDepartments(deptData);
        setJobs(jobData);
      } catch (error) {
        console.error('Failed to fetch form data:', error);
      }
    };
    
    fetchData();
  }, []);

  useEffect(() => {
    if (candidate) {
      setFormData({
        name: candidate.name || "",
        email: candidate.email || "",
        phone: candidate.phone || "",
        summary: candidate.summary || "",
        skill_match_score: candidate.skill_match_score?.toString() || "",
        status: candidate.status?.toString() || "2",
        position_applied: candidate.position_applied || "",
        department_id: candidate.department_id?.toString() || "",
        job_id: candidate.job_id?.toString() || "",
        resume_path: candidate.resume_path || "",
        experience_years: candidate.experience_years?.toString() || "",
        current_salary: candidate.current_salary?.toString() || "",
        expected_salary: candidate.expected_salary?.toString() || "",
        source: candidate.source || "direct"
      });
    }
  }, [candidate]);

  const handleInputChange = (field: string, value: string) => {
    setFormData(prev => ({
      ...prev,
      [field]: value
    }));
    
    // Clear error when user starts typing
    if (errors[field]) {
      setErrors(prev => ({
        ...prev,
        [field]: null
      }));
    }
  };

  const validateForm = () => {
    const newErrors = {};
    
    if (!formData.name.trim()) newErrors.name = "Name is required";
    if (!formData.email.trim()) newErrors.email = "Email is required";
    if (formData.email && !/\S+@\S+\.\S+/.test(formData.email)) {
      newErrors.email = "Invalid email format";
    }
    
    // Only require resume for new candidates (not editing)
    if (!candidate?.id && !resumeFile) {
      newErrors.resume = "Resume file is required";
    }
    
    // Validate file size (10MB max)
    if (resumeFile && resumeFile.size > 10 * 1024 * 1024) {
      newErrors.resume = "File size must be less than 10MB";
    }
    
    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    
    if (!validateForm()) return;
    
    setLoading(true);
    try {
      const submitData = {
        ...formData,
        department_id: formData.department_id ? parseInt(formData.department_id) : null,
        job_id: formData.job_id ? parseInt(formData.job_id) : null,
        experience_years: formData.experience_years ? parseInt(formData.experience_years) : null,
        current_salary: formData.current_salary ? parseFloat(formData.current_salary) : null,
        expected_salary: formData.expected_salary ? parseFloat(formData.expected_salary) : null
      };

      let result;
      if (candidate?.id) {
        // Editing existing candidate - update normally
        result = await updateCandidate(candidate.id, {
          ...submitData,
          skill_match_score: formData.skill_match_score ? parseFloat(formData.skill_match_score) : null,
          status: parseInt(formData.status)
        });
        onSubmit(result);
      } else {
        // New candidate - submit resume for AI processing
        result = await submitCandidateResume(submitData, resumeFile);
        onSubmit({
          message: "Resume submitted for AI processing. Candidate will be added automatically after analysis.",
          type: "resume_submitted"
        });
      }
    } catch (error) {
      console.error('Failed to submit:', error);
      setErrors({ submit: error.message });
    } finally {
      setLoading(false);
    }
  };

  return (
    <Card className="w-full max-w-2xl">
      <CardHeader>
        <CardTitle>{candidate ? 'Edit Candidate' : 'Add New Candidate'}</CardTitle>
      </CardHeader>
      <CardContent>
        <form onSubmit={handleSubmit} className="space-y-4">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div className="space-y-2">
              <Label htmlFor="name">Name *</Label>
              <Input
                id="name"
                value={formData.name}
                onChange={(e) => handleInputChange('name', e.target.value)}
                className={errors.name ? 'border-red-500' : ''}
              />
              {errors.name && <p className="text-sm text-red-500">{errors.name}</p>}
            </div>
            
            <div className="space-y-2">
              <Label htmlFor="email">Email *</Label>
              <Input
                id="email"
                type="email"
                value={formData.email}
                onChange={(e) => handleInputChange('email', e.target.value)}
                className={errors.email ? 'border-red-500' : ''}
              />
              {errors.email && <p className="text-sm text-red-500">{errors.email}</p>}
            </div>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div className="space-y-2">
              <Label htmlFor="phone">Phone</Label>
              <Input
                id="phone"
                value={formData.phone}
                onChange={(e) => handleInputChange('phone', e.target.value)}
              />
            </div>
            
            <div className="space-y-2">
              <Label htmlFor="position_applied">Position Applied</Label>
              <Input
                id="position_applied"
                value={formData.position_applied}
                onChange={(e) => handleInputChange('position_applied', e.target.value)}
              />
            </div>
          </div>

          <div className="space-y-2">
            <Label htmlFor="resume">Resume Upload *</Label>
            <Input
              id="resume"
              type="file"
              accept=".pdf,.doc,.docx"
              onChange={(e) => {
                const file = e.target.files?.[0];
                setResumeFile(file);
                // Clear error when file is selected
                if (errors.resume && file) {
                  setErrors(prev => ({ ...prev, resume: null }));
                }
              }}
              className={errors.resume ? 'border-red-500' : ''}
            />
            <p className="text-sm text-gray-500">Accepted formats: PDF, DOC, DOCX (Max 10MB)</p>
            {errors.resume && <p className="text-sm text-red-500">{errors.resume}</p>}
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div className="space-y-2">
              <Label htmlFor="department_id">Department</Label>
              <Select value={formData.department_id || ""} onValueChange={(value) => handleInputChange('department_id', value)}>
                <SelectTrigger>
                  <SelectValue placeholder="Select Department" />
                </SelectTrigger>
                <SelectContent>
                  {departments.map((dept) => (
                    <SelectItem key={dept.id} value={dept.id.toString()}>
                      {dept.name}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            
            <div className="space-y-2">
              <Label htmlFor="job_id">Job</Label>
              <Select value={formData.job_id || ""} onValueChange={(value) => handleInputChange('job_id', value)}>
                <SelectTrigger>
                  <SelectValue placeholder="Select Job" />
                </SelectTrigger>
                <SelectContent>
                  {jobs.map((job) => (
                    <SelectItem key={job.id} value={job.id.toString()}>
                      {job.title}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div className="space-y-2">
              <Label htmlFor="experience_years">Experience (Years)</Label>
              <Input
                id="experience_years"
                type="number"
                value={formData.experience_years}
                onChange={(e) => handleInputChange('experience_years', e.target.value)}
              />
            </div>
            
            <div className="space-y-2">
              <Label htmlFor="current_salary">Current Salary</Label>
              <Input
                id="current_salary"
                type="number"
                value={formData.current_salary}
                onChange={(e) => handleInputChange('current_salary', e.target.value)}
              />
            </div>
            
            <div className="space-y-2">
              <Label htmlFor="expected_salary">Expected Salary</Label>
              <Input
                id="expected_salary"
                type="number"
                value={formData.expected_salary}
                onChange={(e) => handleInputChange('expected_salary', e.target.value)}
              />
            </div>
          </div>

          <div className="space-y-2">
            <Label htmlFor="source">Source</Label>
            <Select value={formData.source} onValueChange={(value) => handleInputChange('source', value)}>
              <SelectTrigger>
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="direct">Direct Application</SelectItem>
                <SelectItem value="referral">Referral</SelectItem>
                <SelectItem value="linkedin">LinkedIn</SelectItem>
                <SelectItem value="job_board">Job Board</SelectItem>
                <SelectItem value="recruitment_agency">Recruitment Agency</SelectItem>
              </SelectContent>
            </Select>
          </div>

          {errors.submit && (
            <div className="text-sm text-red-500 bg-red-50 p-3 rounded">
              {errors.submit}
            </div>
          )}

          <div className="flex justify-end space-x-2">
            <Button type="button" variant="outline" onClick={onCancel}>
              Cancel
            </Button>
            <Button type="submit" disabled={loading}>
              {loading 
                ? (candidate ? 'Updating...' : 'Submitting Resume...') 
                : (candidate ? 'Update Candidate' : 'Submit Resume')
              }
            </Button>
          </div>
        </form>
      </CardContent>
    </Card>
  );
}
