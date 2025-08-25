import { useState, useEffect } from "react";
import { Plus, RefreshCw, ChevronDown, Trash2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { Badge } from "@/components/ui/badge";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import {
  Dialog,
  DialogContent,
  DialogTrigger,
} from "@/components/ui/dialog";
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
  AlertDialogTrigger,
} from "@/components/ui/alert-dialog";
import { getJobs } from "../services/api.js";
import JobForm from "../components/forms/JobForm.tsx";

export default function Jobs() {
  const [jobs, setJobs] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [showCreateForm, setShowCreateForm] = useState(false);

  // Fetch jobs on component mount
  useEffect(() => {
    const fetchJobs = async () => {
      try {
        setLoading(true);
        const data = await getJobs();
        setJobs(data);
      } catch (error) {
        console.error('Failed to fetch jobs:', error);
      } finally {
        setLoading(false);
      }
    };

    fetchJobs();
  }, []);

  // Refresh data function
  const handleRefresh = async () => {
    try {
      setLoading(true);
      const data = await getJobs();
      setJobs(data);
    } catch (error) {
      console.error('Failed to refresh jobs:', error);
    } finally {
      setLoading(false);
    }
  };

  // Format date for display
  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleDateString();
  };

  // Job status options
  const jobStatuses = [
    { value: "Active", label: "Active", color: "bg-green-600" },
    { value: "On Hold", label: "On Hold", color: "bg-yellow-600" },
    { value: "Completed", label: "Completed", color: "bg-blue-600" },
    { value: "Canceled", label: "Canceled", color: "bg-red-600" }
  ];

  // Get status color
  const getStatusColor = (status: string) => {
    const statusObj = jobStatuses.find(s => s.value === status);
    return statusObj ? statusObj.color : "bg-gray-600";
  };

  // Handle status change
  const handleStatusChange = (jobId: number, newStatus: string) => {
    // Update the job status in the local state
    setJobs(jobs.map(job => 
      job.id === jobId ? { ...job, status: newStatus } : job
    ));
    
    // Here you would typically make an API call to update the status in the database
    // updateJobStatus(jobId, newStatus);
    console.log(`Job ${jobId} status changed to ${newStatus}`);
  };

  // Handle form submit (create job)
  const handleFormSubmit = async (jobData: any) => {
    try {
      await handleRefresh(); // Refresh the list
      setShowCreateForm(false);
    } catch (error) {
      console.error('Failed to save job:', error);
    }
  };

  // Handle delete job
  const handleDeleteJob = async (jobId: number) => {
    try {
      const response = await fetch(`/api/jobs/${jobId}`, {
        method: 'DELETE',
        headers: {
          'Authorization': `Bearer ${localStorage.getItem('auth_token')}`
        }
      });

      if (response.ok) {
        await handleRefresh(); // Refresh the list
      } else {
        const error = await response.json();
        console.error('Failed to delete job:', error);
        alert('Failed to delete job: ' + (error.error || 'Unknown error'));
      }
    } catch (error) {
      console.error('Error deleting job:', error);
      alert('Network error. Please try again.');
    }
  };

  return (
    <div className="h-full flex flex-col">
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-bold text-foreground">Jobs</h1>
        <Button variant="outline" size="sm" className="flex items-center space-x-2" onClick={handleRefresh} disabled={loading}>
          <RefreshCw className={`h-4 w-4 ${loading ? 'animate-spin' : ''}`} />
          <span>Refresh</span>
        </Button>
      </div>

      {/* Create Job Button */}
      <div className="mb-6">
        <Dialog open={showCreateForm} onOpenChange={setShowCreateForm}>
          <DialogTrigger asChild>
            <Button className="flex items-center space-x-2" data-create-job>
              <Plus className="h-4 w-4" />
              <span>Create Job</span>
            </Button>
          </DialogTrigger>
          <DialogContent className="max-w-4xl">
            <JobForm
              onSubmit={handleFormSubmit}
              onCancel={() => setShowCreateForm(false)}
            />
          </DialogContent>
        </Dialog>
      </div>

      {/* Jobs Table with Fixed Headers */}
      <div className="flex-1 overflow-hidden">
        <Card className="h-full flex flex-col">
          {/* Fixed Header */}
          <div className="bg-muted/50 border-b border-border p-0 flex-shrink-0">
            <div className="grid grid-cols-6 gap-4 p-4 font-semibold text-sm">
              <div>Job Title</div>
              <div>Department Name</div>
              <div>Posted By</div>
              <div>Status</div>
              <div>Job Opening Creation Date</div>
              <div>Actions</div>
            </div>
          </div>
          
          {/* Scrollable Content */}
          <div className="flex-1 overflow-y-auto hide-scrollbar">
            {loading ? (
              <div className="flex justify-center items-center py-12">
                <p className="text-muted-foreground">Loading jobs...</p>
              </div>
            ) : jobs.length === 0 ? (
              <div className="flex justify-center items-center py-12">
                <p className="text-muted-foreground">No jobs available</p>
              </div>
            ) : (
              <div className="divide-y divide-border">
                {jobs.map((job, index) => (
                  <div key={job.id || index} className="grid grid-cols-6 gap-4 p-4 hover:bg-muted/50 transition-colors items-center">
                    <div className="font-medium">
                      <div>{job.title}</div>
                      {job.public_link && (
                        <div className="text-xs text-blue-600 mt-1">
                          <a href={job.public_link} target="_blank" rel="noopener noreferrer" className="hover:underline">
                            Application Link: {job.application_code}
                          </a>
                        </div>
                      )}
                    </div>
                    <div className="text-sm text-muted-foreground">{job.department_name || 'No Department'}</div>
                    <div className="text-sm text-muted-foreground">
                      {job.posted_by_name || 'Unknown User'}
                    </div>
                    <div className="flex items-center">
                      <DropdownMenu>
                        <DropdownMenuTrigger asChild>
                          <div className="cursor-pointer inline-block">
                            <Badge 
                              className={`${getStatusColor(job.status)} text-white hover:opacity-80 transition-opacity inline-flex items-center space-x-1 px-2 py-1 text-xs font-medium rounded-md`}
                            >
                              <span>{job.status}</span>
                              <ChevronDown className="h-3 w-3 ml-1" />
                            </Badge>
                          </div>
                        </DropdownMenuTrigger>
                        <DropdownMenuContent align="start">
                          {jobStatuses.map((status) => (
                            <DropdownMenuItem
                              key={status.value}
                              onClick={() => handleStatusChange(job.id || index, status.value)}
                              className="flex items-center space-x-2 cursor-pointer"
                            >
                              <div className={`w-3 h-3 rounded-full ${status.color}`}></div>
                              <span>{status.label}</span>
                            </DropdownMenuItem>
                          ))}
                        </DropdownMenuContent>
                      </DropdownMenu>
                    </div>
                    <div className="text-sm text-muted-foreground flex items-center">{formatDate(job.created_at || job.createdDate)}</div>
                    <div className="flex items-center justify-center">
                      <AlertDialog>
                        <AlertDialogTrigger asChild>
                          <Button
                            variant="outline"
                            size="sm"
                            className="text-red-600 hover:text-red-700 hover:bg-red-50"
                          >
                            <Trash2 className="h-4 w-4" />
                          </Button>
                        </AlertDialogTrigger>
                        <AlertDialogContent>
                          <AlertDialogHeader>
                            <AlertDialogTitle>Delete Job</AlertDialogTitle>
                            <AlertDialogDescription>
                              Are you sure you want to delete the job "{job.title}"? 
                              This action cannot be undone and will remove all associated applications and data.
                            </AlertDialogDescription>
                          </AlertDialogHeader>
                          <AlertDialogFooter>
                            <AlertDialogCancel>Cancel</AlertDialogCancel>
                            <AlertDialogAction
                              onClick={() => handleDeleteJob(job.id)}
                              className="bg-red-600 hover:bg-red-700"
                            >
                              Delete
                            </AlertDialogAction>
                          </AlertDialogFooter>
                        </AlertDialogContent>
                      </AlertDialog>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </Card>
      </div>
    </div>
  );
}
