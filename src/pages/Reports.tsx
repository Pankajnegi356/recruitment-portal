import { useState, useEffect, useMemo } from "react";
import { 
  Calendar, 
  Users, 
  Briefcase, 
  TrendingUp, 
  Clock, 
  Target, 
  Download, 
  Filter,
  BarChart3,
  PieChart as PieChartIcon,
  RefreshCw,
  FileText,
  Award
} from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { 
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { 
  PieChart, 
  Pie, 
  Cell, 
  ResponsiveContainer, 
  Legend, 
  Tooltip, 
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  BarChart,
  Bar,
  FunnelChart,
  Funnel,
  LabelList
} from "recharts";
import { getCandidates, getJobs, getDashboardStats } from "../services/api.js";
import { getStatusLabel } from "../config/database.js";

interface KPIData {
  label: string;
  value: string | number;
  change: string;
  trend: 'up' | 'down' | 'neutral';
  icon: any;
  color: string;
}

export default function Reports() {
  const [candidates, setCandidates] = useState<any[]>([]);
  const [jobs, setJobs] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [dateRange, setDateRange] = useState('30');
  const [departmentFilter, setDepartmentFilter] = useState('all');

  // Fetch data on component mount
  useEffect(() => {
    const fetchData = async () => {
      try {
        setLoading(true);
        const [candidatesData, jobsData] = await Promise.all([
          getCandidates(),
          getJobs()
        ]);
        setCandidates(candidatesData);
        setJobs(jobsData);
      } catch (error) {
        console.error('Failed to fetch reports data:', error);
      } finally {
        setLoading(false);
      }
    };

    fetchData();
  }, []);

  // Calculate KPI data using only real data
  const kpiData: KPIData[] = useMemo(() => {
    const totalApplications = candidates.length;
    const shortlistedCount = candidates.filter(c => c.status >= 2).length;
    const interviewCount = candidates.filter(c => c.status >= 4).length;
    const conversionRate = totalApplications > 0 ? Math.round((interviewCount / totalApplications) * 100) : 0;
    const activeJobs = jobs.filter(j => j.status === 'Active').length;

    return [
      {
        label: "Total Applications",
        value: totalApplications,
        change: "Real Data",
        trend: 'neutral' as const,
        icon: Users,
        color: 'text-blue-600'
      },
      {
        label: "Shortlisted",
        value: shortlistedCount,
        change: "Real Data",
        trend: 'neutral' as const,
        icon: Target,
        color: 'text-green-600'
      },
      {
        label: "In Interview Process",
        value: interviewCount,
        change: "Real Data",
        trend: 'neutral' as const,
        icon: Clock,
        color: 'text-purple-600'
      },
      {
        label: "Active Jobs",
        value: activeJobs,
        change: "Real Data",
        trend: 'neutral' as const,
        icon: Briefcase,
        color: 'text-orange-600'
      }
    ];
  }, [candidates, jobs]);

  // Application trends based on actual candidate creation dates
  const applicationTrends = useMemo(() => {
    const last7Days = [];
    const today = new Date();
    
    // Generate last 7 days
    for (let i = 6; i >= 0; i--) {
      const date = new Date(today);
      date.setDate(today.getDate() - i);
      const dayName = date.toLocaleDateString('en-US', { weekday: 'short' });
      
      // Count applications for this day
      const applicationsCount = candidates.filter(candidate => {
        const candidateDate = new Date(candidate.created_at);
        return candidateDate.toDateString() === date.toDateString();
      }).length;
      
      last7Days.push({
        day: dayName,
        applications: applicationsCount
      });
    }
    
    return last7Days;
  }, [candidates]);

  // Candidate pipeline data
  const pipelineData = useMemo(() => [
    { name: 'Applied', value: candidates.length, color: '#3b82f6' },
    { name: 'Shortlisted', value: candidates.filter(c => c.status >= 2).length, color: '#10b981' },
    { name: 'Assessment', value: candidates.filter(c => c.status >= 3).length, color: '#f59e0b' },
    { name: 'Interview', value: candidates.filter(c => c.status >= 4).length, color: '#8b5cf6' },
    { name: 'Interview Cleared', value: candidates.filter(c => c.status >= 6).length, color: '#06b6d4' }
  ], [candidates]);

  // Job status distribution
  const jobStatusData = useMemo(() => {
    const statusCounts = jobs.reduce((acc: any, job: any) => {
      const status = job?.status || 'Unknown';
      acc[status] = (acc[status] || 0) + 1;
      return acc;
    }, {});

    return Object.entries(statusCounts).map(([status, count]) => ({
      name: status,
      value: count as number
    }));
  }, [jobs]);

  // Department performance data
  const departmentData = useMemo(() => {
    const deptStats = jobs.reduce((acc: any, job: any) => {
      const dept = job.department_name || job.department || 'Unknown';
      if (!acc[dept]) {
        acc[dept] = { applications: 0, jobs: 0 };
      }
      acc[dept].jobs++;
      // Count applications for this department by job_id
      acc[dept].applications += candidates.filter(c => c.job_id === job.id).length;
      return acc;
    }, {});

    return Object.entries(deptStats).map(([dept, stats]: [string, any]) => ({
      department: dept,
      applications: stats.applications,
      jobs: stats.jobs
    }));
  }, [jobs, candidates]);

  // Recent hiring summary
  const recentHiring = useMemo(() => {
    return jobs.slice(0, 5).map(job => ({
      jobTitle: job.title,
      department: job.department_name || job.department || 'Unknown',
      applications: candidates.filter(c => c.job_id === job.id).length,
      shortlisted: candidates.filter(c => c.job_id === job.id && c.status >= 2).length,
      interviews: candidates.filter(c => c.job_id === job.id && c.status >= 4).length,
      status: job.status,
      datePosted: new Date(job.created_at).toLocaleDateString()
    }));
  }, [jobs, candidates]);

  // Colors for charts
  const CHART_COLORS = {
    'Active': '#10b981',
    'On Hold': '#f59e0b', 
    'Completed': '#3b82f6',
    'Canceled': '#ef4444'
  };

  const handleRefresh = async () => {
    setLoading(true);
    // Simulate API call
    setTimeout(() => {
      setLoading(false);
    }, 1000);
  };

  const handleExport = (format: string) => {
    console.log(`Exporting reports as ${format}`);
    // Implementation for PDF/Excel export
  };

  return (
    <div className="h-full flex flex-col">
      <div className="flex-1 overflow-y-auto hide-scrollbar space-y-6 p-1">
      {/* Header */}
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold text-foreground">Reports & Analytics</h1>
        <div className="flex items-center space-x-3">
          {/* Filters */}
          <Select value={dateRange} onValueChange={setDateRange}>
            <SelectTrigger className="w-32">
              <SelectValue placeholder="Date Range" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="7">Last 7 days</SelectItem>
              <SelectItem value="30">Last 30 days</SelectItem>
              <SelectItem value="90">Last 3 months</SelectItem>
              <SelectItem value="365">Last year</SelectItem>
            </SelectContent>
          </Select>

          <Select value={departmentFilter} onValueChange={setDepartmentFilter}>
            <SelectTrigger className="w-40">
              <SelectValue placeholder="Department" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">All Departments</SelectItem>
              <SelectItem value="ai">Artificial Intelligence</SelectItem>
              <SelectItem value="dev">Software Development</SelectItem>
            </SelectContent>
          </Select>

          {/* Export Options */}
          <Button variant="outline" size="sm" onClick={() => handleExport('pdf')}>
            <Download className="h-4 w-4 mr-2" />
            Export PDF
          </Button>
          
          <Button variant="outline" size="sm" onClick={handleRefresh} disabled={loading}>
            <RefreshCw className={`h-4 w-4 mr-2 ${loading ? 'animate-spin' : ''}`} />
            Refresh
          </Button>
        </div>
      </div>

      {/* KPI Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        {kpiData.map((kpi, index) => {
          const IconComponent = kpi.icon;
          return (
            <Card key={index} className="hover:shadow-md transition-shadow">
              <CardContent className="p-4">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-sm text-muted-foreground">{kpi.label}</p>
                    <p className="text-2xl font-bold">{kpi.value}</p>
                  </div>
                  <IconComponent className={`h-8 w-8 ${kpi.color}`} />
                </div>
              </CardContent>
            </Card>
          );
        })}
      </div>

      {/* Charts Section */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Application Trends */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center space-x-2">
              <TrendingUp className="h-5 w-5" />
              <span>Application Trends</span>
            </CardTitle>
          </CardHeader>
          <CardContent>
            <ResponsiveContainer width="100%" height={250}>
              <LineChart data={applicationTrends}>
                <CartesianGrid strokeDasharray="3 3" className="opacity-30" />
                <XAxis dataKey="day" />
                <YAxis />
                <Tooltip />
                <Line 
                  type="monotone" 
                  dataKey="applications" 
                  stroke="#3b82f6" 
                  strokeWidth={2}
                  dot={{ fill: '#3b82f6', strokeWidth: 2, r: 4 }}
                />
              </LineChart>
            </ResponsiveContainer>
          </CardContent>
        </Card>

        {/* Candidate Pipeline */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center space-x-2">
              <Users className="h-5 w-5" />
              <span>Candidate Pipeline</span>
            </CardTitle>
          </CardHeader>
          <CardContent>
            <ResponsiveContainer width="100%" height={250}>
              <BarChart data={pipelineData}>
                <CartesianGrid strokeDasharray="3 3" className="opacity-30" />
                <XAxis dataKey="name" />
                <YAxis />
                <Tooltip />
                <Bar dataKey="value" fill="#3b82f6" radius={[4, 4, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </CardContent>
        </Card>

        {/* Job Status Distribution */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center space-x-2">
              <PieChartIcon className="h-5 w-5" />
              <span>Job Status Distribution</span>
            </CardTitle>
          </CardHeader>
          <CardContent>
            <ResponsiveContainer width="100%" height={250}>
              <PieChart>
                <Pie
                  data={jobStatusData}
                  cx="50%"
                  cy="50%"
                  innerRadius={60}
                  outerRadius={100}
                  paddingAngle={5}
                  dataKey="value"
                >
                  {jobStatusData.map((entry, index) => (
                    <Cell 
                      key={`cell-${index}`} 
                      fill={CHART_COLORS[entry.name as keyof typeof CHART_COLORS] || '#8884d8'} 
                    />
                  ))}
                </Pie>
                <Tooltip />
                <Legend />
              </PieChart>
            </ResponsiveContainer>
          </CardContent>
        </Card>

        {/* Department Performance */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center space-x-2">
              <BarChart3 className="h-5 w-5" />
              <span>Department Performance</span>
            </CardTitle>
          </CardHeader>
          <CardContent>
            <ResponsiveContainer width="100%" height={250}>
              <BarChart data={departmentData}>
                <CartesianGrid strokeDasharray="3 3" className="opacity-30" />
                <XAxis dataKey="department" />
                <YAxis />
                <Tooltip />
                <Bar dataKey="applications" fill="#3b82f6" name="Applications" />
                <Bar dataKey="jobs" fill="#10b981" name="Job Openings" />
              </BarChart>
            </ResponsiveContainer>
          </CardContent>
        </Card>
      </div>

      {/* Recent Hiring Summary Table */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center space-x-2">
            <FileText className="h-5 w-5" />
            <span>Recent Hiring Summary</span>
          </CardTitle>
        </CardHeader>
        <CardContent>
          <Table>
            <TableHeader>
              <TableRow className="bg-muted/50">
                <TableHead className="font-semibold">Job Title</TableHead>
                <TableHead className="font-semibold">Department</TableHead>
                <TableHead className="font-semibold">Applications</TableHead>
                <TableHead className="font-semibold">Shortlisted</TableHead>
                <TableHead className="font-semibold">Interviews</TableHead>
                <TableHead className="font-semibold">Status</TableHead>
                <TableHead className="font-semibold">Date Posted</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {recentHiring.map((item, index) => (
                <TableRow key={index} className="hover:bg-muted/30 transition-colors">
                  <TableCell className="font-medium">{item.jobTitle}</TableCell>
                  <TableCell>{item.department}</TableCell>
                  <TableCell>
                    <Badge variant="secondary">{item.applications}</Badge>
                  </TableCell>
                  <TableCell>
                    <Badge variant="secondary">{item.shortlisted}</Badge>
                  </TableCell>
                  <TableCell>
                    <Badge variant="secondary">{item.interviews}</Badge>
                  </TableCell>
                  <TableCell>
                    <Badge 
                      className={`${
                        item.status === 'Active' ? 'bg-green-100 text-green-800' :
                        item.status === 'On Hold' ? 'bg-yellow-100 text-yellow-800' :
                        item.status === 'Completed' ? 'bg-blue-100 text-blue-800' :
                        'bg-red-100 text-red-800'
                      }`}
                    >
                      {item.status}
                    </Badge>
                  </TableCell>
                  <TableCell className="text-muted-foreground">{item.datePosted}</TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </CardContent>
      </Card>
      </div>
    </div>
  );
}
