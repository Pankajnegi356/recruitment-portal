import { useState, useEffect } from "react";
import { Plus, RefreshCw, ChevronDown } from "lucide-react";
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
import { getJobs } from "../services/api.js";

export default function Jobs() {
  const [jobs, setJobs] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);

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

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold text-foreground">Jobs</h1>
        <Button variant="outline" size="sm" className="flex items-center space-x-2" onClick={handleRefresh} disabled={loading}>
          <RefreshCw className={`h-4 w-4 ${loading ? 'animate-spin' : ''}`} />
          <span>Refresh</span>
        </Button>
      </div>

      {/* Create Job Button */}
      <div>
        <Button className="flex items-center space-x-2">
          <Plus className="h-4 w-4" />
          <span>Create Job</span>
        </Button>
      </div>

      {/* Jobs Table */}
      <Card>
        <CardContent className="p-0">
          <Table>
            <TableHeader>
              <TableRow className="bg-muted/50">
                <TableHead className="font-semibold text-table-header">Job Title</TableHead>
                <TableHead className="font-semibold text-table-header">Department Name</TableHead>
                <TableHead className="font-semibold text-table-header">Department Team</TableHead>
                <TableHead className="font-semibold text-table-header">Status</TableHead>
                <TableHead className="font-semibold text-table-header">Job Opening Creation Date</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {loading ? (
                <TableRow>
                  <TableCell colSpan={5} className="text-center py-8">
                    <p className="text-muted-foreground">Loading jobs...</p>
                  </TableCell>
                </TableRow>
              ) : jobs.length === 0 ? (
                <TableRow>
                  <TableCell colSpan={5} className="text-center py-8">
                    <p className="text-muted-foreground">No jobs available</p>
                  </TableCell>
                </TableRow>
              ) : (
                jobs.map((job, index) => (
                  <TableRow key={job.id || index} className="hover:bg-table-row-hover transition-colors">
                    <TableCell className="font-medium">{job.title}</TableCell>
                    <TableCell>{job.department}</TableCell>
                    <TableCell>{job.team}</TableCell>
                    <TableCell>
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
                    </TableCell>
                    <TableCell className="text-muted-foreground">{formatDate(job.created_at || job.createdDate)}</TableCell>
                  </TableRow>
                ))
              )}
            </TableBody>
          </Table>
        </CardContent>
      </Card>
    </div>
  );
}
