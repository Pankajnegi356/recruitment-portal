import { useState, useEffect } from "react";
import { 
  Clock, 
  Users, 
  Briefcase, 
  Calendar, 
  CheckCircle, 
  AlertCircle, 
  User, 
  FileText, 
  MessageSquare,
  TrendingUp,
  RefreshCw,
  Filter,
  Bell,
  ArrowRight,
  UserCheck,
  UserPlus,
  Award,
  Send,
  Eye,
  Plus
} from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Dialog, DialogContent, DialogTrigger } from "@/components/ui/dialog";
import { getCandidates, getJobs, getDashboardStats, getInterviews } from "../services/api.js";
import { getStatusLabel, getStatusColor } from "../config/database.js";
import TaskForm from "../components/forms/TaskForm.tsx";

interface ActivityItem {
  id: number;
  type: 'candidate' | 'job' | 'interview' | 'offer' | 'system' | 'status_change';
  title: string;
  description: string;
  user: string;
  timestamp: string;
  priority: 'high' | 'medium' | 'low';
  candidate?: any;
  job?: any;
}

interface QuickStat {
  label: string;
  value: number;
  icon: any;
  color: string;
  trend?: number;
}

export default function Activity() {
  const [activities, setActivities] = useState<ActivityItem[]>([]);
  const [candidates, setCandidates] = useState<any[]>([]);
  const [jobs, setJobs] = useState<any[]>([]);
  const [loading, setLoading] = useState(false);
  const [filter, setFilter] = useState('all');
  const [showTaskForm, setShowTaskForm] = useState(false);

  // Load all data and generate activity feed
  useEffect(() => {
    loadActivityData();
  }, []);

  const loadActivityData = async () => {
    try {
      setLoading(true);
      
      // Fetch all data in parallel
      const [candidatesData, jobsData, interviewsData, statsData] = await Promise.all([
        getCandidates(),
        getJobs(),
        getInterviews(),
        getDashboardStats()
      ]);
      
      setCandidates(candidatesData);
      setJobs(jobsData);
      
      // Generate activity feed from real data
      const generatedActivities = generateActivityFeed(
        candidatesData, 
        jobsData, 
        interviewsData
      );
      
      setActivities(generatedActivities);
    } catch (error) {
      console.error('Failed to load activity data:', error);
    } finally {
      setLoading(false);
    }
  };

  // Generate activity feed from actual data
  const generateActivityFeed = (candidatesData: any[], jobsData: any[], interviewsData: any[]) => {
    const activities: ActivityItem[] = [];
    let activityId = 1;

    // Generate candidate activities - show all progression stages for each candidate
    candidatesData.forEach(candidate => {
      const appliedDate = new Date(candidate.created_at);
      const timeAgo = getTimeAgo(appliedDate);
      
      // Generate all progression stages based on current status (newest first)
      const progressionStages = [];
      
      // Application submitted (status 1)
      progressionStages.push({
        id: activityId++,
        type: 'candidate',
        title: 'New Application Received',
        description: `${candidate.name} applied for ${candidate.position_applied || candidate.job_title || candidate.appliedFor || 'General Application'}`,
        user: 'System',
        timestamp: timeAgo,
        priority: 'high',
        candidate
      });
      
      // For rejected candidates, show their progression before rejection
      const isRejected = candidate.status === 0;
      const maxStatusReached = isRejected ? (candidate.max_status_reached || 5) : candidate.status;
      const statusToCheck = isRejected ? maxStatusReached : candidate.status;
      
      // Add progression stages based on max status reached (for rejected) or current status
      if (statusToCheck >= 2) {
        progressionStages.push({
          id: activityId++,
          type: 'status_change',
          title: 'Candidate Shortlisted',
          description: `${candidate.name} moved to Shortlisted stage`,
          user: 'HR Team',
          timestamp: timeAgo,
          priority: 'medium',
          candidate
        });
      }
      
      if (statusToCheck >= 3) {
        progressionStages.push({
          id: activityId++,
          type: 'status_change',
          title: 'Pre-screening Test Assigned',
          description: `${candidate.name} moved to Pre-screening Test stage`,
          user: 'HR Team',
          timestamp: timeAgo,
          priority: 'medium',
          candidate
        });
      }
      
      if (statusToCheck >= 4) {
        progressionStages.push({
          id: activityId++,
          type: 'interview',
          title: 'Interview Date Negotiation',
          description: `${candidate.name} moved to Negotiating Interview Date stage`,
          user: 'HR Team',
          timestamp: timeAgo,
          priority: 'high',
          candidate
        });
      }
      
      if (statusToCheck >= 5) {
        progressionStages.push({
          id: activityId++,
          type: 'interview',
          title: 'Interview Confirmed',
          description: `${candidate.name} moved to Interview Confirmed stage`,
          user: 'HR Team',
          timestamp: timeAgo,
          priority: 'high',
          candidate
        });
      }
      
      if (statusToCheck >= 6) {
        progressionStages.push({
          id: activityId++,
          type: 'status_change',
          title: 'Interview Cleared',
          description: `${candidate.name} cleared interview - moved to Round 2`,
          user: 'HR Team',
          timestamp: timeAgo,
          priority: 'high',
          candidate
        });
      }
      
      // Handle rejection status (0) - show this as the final step
      if (isRejected) {
        progressionStages.push({
          id: activityId++,
          type: 'status_change',
          title: 'Candidate Rejected',
          description: `${candidate.name} was rejected`,
          user: 'HR Team',
          timestamp: timeAgo,
          priority: 'medium',
          candidate
        });
      }
      
      // Add all stages to activities (newest first, so reverse the progression)
      activities.push(...progressionStages.reverse());
    });

    // Generate job posting activities
    jobsData.forEach(job => {
      activities.push({
        id: activityId++,
        type: 'job',
        title: 'New Job Posted',
        description: `${job.title} position published in ${job.department_name || job.department || 'department'}`,
        user: job.team || 'HR Team',
        timestamp: getTimeAgo(new Date(job.created_at)),
        priority: 'low',
        job
      });
    });

    // Add system notifications based on data
    const todayApplications = candidatesData.filter(c => 
      isToday(new Date(c.created_at))
    ).length;
    
    if (todayApplications > 0) {
      // Use the most recent application time for system notification
      const mostRecentApplication = candidatesData
        .filter(c => isToday(new Date(c.created_at)))
        .sort((a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime())[0];
      
      activities.push({
        id: activityId++,
        type: 'system',
        title: 'Daily Application Summary',
        description: `${todayApplications} new applications received today`,
        user: 'System',
        timestamp: mostRecentApplication ? getTimeAgo(new Date(mostRecentApplication.created_at)) : 'just now',
        priority: 'medium'
      });
    }

    // Add urgent reminders
    const interviewPendingCandidates = candidatesData.filter(c => c.status === 4 || c.status === 5);
    if (interviewPendingCandidates.length > 0) {
      activities.push({
        id: activityId++,
        type: 'system',
        title: 'Interview Follow-up Required',
        description: `${interviewPendingCandidates.length} candidates pending interview feedback`,
        user: 'System',
        timestamp: '30 minutes ago',
        priority: 'high'
      });
    }

    // Sort activities by timestamp and ensure job postings come before applications
    return activities.sort((a, b) => {
      // First, sort by actual creation time for proper chronological order
      if (a.job && b.candidate) {
        // Job posting should come before candidate application
        const jobDate = new Date(a.job.created_at);
        const candidateDate = new Date(b.candidate.created_at);
        return candidateDate.getTime() - jobDate.getTime(); // Reverse for newest first
      }
      if (a.candidate && b.job) {
        // Job posting should come before candidate application
        const candidateDate = new Date(a.candidate.created_at);
        const jobDate = new Date(b.job.created_at);
        return candidateDate.getTime() - jobDate.getTime(); // Reverse for newest first
      }
      
      // For other activities, sort by parsed time
      const timeA = parseTimeAgo(a.timestamp);
      const timeB = parseTimeAgo(b.timestamp);
      return timeA - timeB;
    });
  };

  // Helper function to calculate time ago
  const getTimeAgo = (date: Date) => {
    const now = new Date();
    const diffMs = now.getTime() - date.getTime();
    const diffMins = Math.floor(diffMs / 60000);
    const diffHours = Math.floor(diffMs / 3600000);
    const diffDays = Math.floor(diffMs / 86400000);

    if (diffMins < 1) {
      return `just now`;
    } else if (diffMins < 60) {
      return `${diffMins} minute${diffMins !== 1 ? 's' : ''} ago`;
    } else if (diffHours < 24) {
      return `${diffHours} hour${diffHours !== 1 ? 's' : ''} ago`;
    } else {
      return `${diffDays} day${diffDays !== 1 ? 's' : ''} ago`;
    }
  };

  // Helper to check if date is today
  const isToday = (date: Date) => {
    const today = new Date();
    return date.toDateString() === today.toDateString();
  };

  // Helper to parse time ago for sorting
  const parseTimeAgo = (timeAgo: string): number => {
    const match = timeAgo.match(/(\d+)\s+(minute|hour|day)/);
    if (!match) return 0;
    
    const value = parseInt(match[1]);
    const unit = match[2];
    
    switch (unit) {
      case 'minute': return value;
      case 'hour': return value * 60;
      case 'day': return value * 24 * 60;
      default: return 0;
    }
  };

  // Calculate quick stats from real data
  const quickStats: QuickStat[] = [
    { 
      label: "Today's Applications", 
      value: candidates.filter(c => isToday(new Date(c.created_at))).length, 
      icon: Users, 
      color: 'text-blue-600'
    },
    { 
      label: 'Pending Interviews', 
      value: candidates.filter(c => c.status === 4 || c.status === 5).length, 
      icon: Calendar, 
      color: 'text-green-600'
    },
    { 
      label: 'Active Jobs', 
      value: jobs.filter(j => j.status === 'active' || j.status === 'Active').length, 
      icon: Briefcase, 
      color: 'text-purple-600'
    },
    { 
      label: 'Urgent Actions', 
      value: candidates.filter(c => c.status === 4 || c.status === 5).length + jobs.filter(j => j.status === 'active' || j.status === 'Active').length, 
      icon: AlertCircle, 
      color: 'text-red-600'
    }
  ];

  // Generate real pending tasks from data
  const pendingTasks = [
    ...candidates
      .filter(c => isToday(new Date(c.created_at)))
      .slice(0, 3)
      .map(c => ({
        id: c.id,
        task: `Review application: ${c.name}`,
        priority: 'high' as const,
        due: 'Today'
      })),
    ...candidates
      .filter(c => c.status === 4 || c.status === 5)
      .slice(0, 2)
      .map(c => ({
        id: c.id + 1000,
        task: `Schedule interview with ${c.name}`,
        priority: 'high' as const,
        due: 'Today'
      })),
    {
      id: 9999,
      task: 'Update job descriptions for active positions',
      priority: 'medium' as const,
      due: 'This week'
    }
  ];

  const getActivityIcon = (type: string) => {
    switch (type) {
      case 'candidate': return UserPlus;
      case 'status_change': return UserCheck;
      case 'job': return Briefcase;
      case 'interview': return Calendar;
      case 'offer': return Send;
      case 'system': return Bell;
      default: return Clock;
    }
  };

  const getPriorityColor = (priority: string) => {
    switch (priority) {
      case 'high': return 'text-red-600 bg-red-50 border-red-200';
      case 'medium': return 'text-yellow-600 bg-yellow-50 border-yellow-200';
      case 'low': return 'text-green-600 bg-green-50 border-green-200';
      default: return 'text-gray-600 bg-gray-50 border-gray-200';
    }
  };

  const getTaskPriorityColor = (priority: string) => {
    switch (priority) {
      case 'high': return 'bg-red-500';
      case 'medium': return 'bg-yellow-500';
      case 'low': return 'bg-green-500';
      default: return 'bg-gray-500';
    }
  };

  const filteredActivities = filter === 'all' 
    ? activities 
    : activities.filter(activity => activity.type === filter);

  const handleRefresh = async () => {
    await loadActivityData();
  };

  const handleTaskSubmit = async (task: any) => {
    console.log('Task created successfully:', task);
    setShowTaskForm(false);
    // Optionally refresh activity data to show the new task in the activity feed
    await loadActivityData();
  };

  const handleTaskCancel = () => {
    setShowTaskForm(false);
  };

  return (
    <div className="space-y-4">
      {/* Header - matching other pages */}
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold text-foreground">Activity Center</h1>
        <Button 
          variant="outline" 
          size="sm" 
          onClick={handleRefresh}
          disabled={loading}
          className="flex items-center space-x-2"
        >
          <RefreshCw className={`h-4 w-4 ${loading ? 'animate-spin' : ''}`} />
          <span>Refresh</span>
        </Button>
      </div>

      {/* Quick Stats */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        {quickStats.map((stat, index) => {
          const IconComponent = stat.icon;
          return (
            <Card key={index} className="hover:shadow-md transition-shadow">
              <CardContent className="p-4">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-sm text-muted-foreground">{stat.label}</p>
                    <div className="flex items-center space-x-2">
                      <p className="text-2xl font-bold">{stat.value}</p>
                      {stat.trend && (
                        <Badge variant="secondary" className={`text-xs ${stat.trend > 0 ? 'text-green-600 bg-green-50' : 'text-red-600 bg-red-50'}`}>
                          {stat.trend > 0 ? '+' : ''}{stat.trend}
                        </Badge>
                      )}
                    </div>
                  </div>
                  <IconComponent className={`h-8 w-8 ${stat.color}`} />
                </div>
              </CardContent>
            </Card>
          );
        })}
      </div>

      {/* Main Content - Activity Feed and Pending Tasks */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        {/* Activity Feed */}
        <Card className="h-96 flex flex-col">
          <CardHeader>
            <div className="flex items-center justify-between">
              <CardTitle className="flex items-center space-x-2">
                <TrendingUp className="h-5 w-5" />
                <span>Recent Activity</span>
              </CardTitle>
              <Tabs value={filter} onValueChange={setFilter} className="w-auto">
                <TabsList className="grid grid-cols-6 w-full">
                  <TabsTrigger value="all" className="text-xs">All</TabsTrigger>
                  <TabsTrigger value="candidate" className="text-xs">Candidates</TabsTrigger>
                  <TabsTrigger value="job" className="text-xs">Jobs</TabsTrigger>
                  <TabsTrigger value="interview" className="text-xs">Interviews</TabsTrigger>
                  <TabsTrigger value="offer" className="text-xs">Offers</TabsTrigger>
                  <TabsTrigger value="system" className="text-xs">System</TabsTrigger>
                </TabsList>
              </Tabs>
            </div>
          </CardHeader>
          <CardContent className="flex-1 overflow-y-auto">
            <div className="space-y-2">
              {filteredActivities.length > 0 ? (
                filteredActivities.map((activity) => {
                  const IconComponent = getActivityIcon(activity.type);
                  return (
                    <div key={activity.id} className="flex items-center space-x-3 p-2 rounded-lg hover:bg-muted/30 transition-colors">
                      <div className="flex-shrink-0">
                        <IconComponent className="h-4 w-4 text-blue-600" />
                      </div>
                      <div className="flex-1 min-w-0">
                        <p className="text-sm text-foreground truncate">{activity.description}</p>
                      </div>
                      <span className="text-xs text-muted-foreground flex-shrink-0">{activity.timestamp}</span>
                    </div>
                  );
                })
              ) : (
                <div className="flex items-center justify-center h-32">
                  <p className="text-muted-foreground">No activities found</p>
                </div>
              )}
            </div>
          </CardContent>
        </Card>

        {/* Pending Tasks */}
        <Card className="h-96 flex flex-col">
          <CardHeader>
            <div className="flex items-center justify-between">
              <CardTitle className="flex items-center space-x-2">
                <CheckCircle className="h-5 w-5 text-blue-600" />
                <span>Pending Tasks</span>
                <Badge variant="secondary">{pendingTasks.length}</Badge>
              </CardTitle>
              <Dialog open={showTaskForm} onOpenChange={setShowTaskForm}>
                <DialogTrigger asChild>
                  <Button size="sm" className="flex items-center space-x-1" data-create-task>
                    <Plus className="h-3 w-3" />
                    <span className="text-xs">Create Task</span>
                  </Button>
                </DialogTrigger>
                <DialogContent className="max-w-4xl max-h-[90vh] overflow-y-auto">
                  <TaskForm 
                    onSubmit={handleTaskSubmit}
                    onCancel={handleTaskCancel}
                  />
                </DialogContent>
              </Dialog>
            </div>
          </CardHeader>
          <CardContent className="flex-1 overflow-y-auto">
            <div className="space-y-2">
              {pendingTasks.length > 0 ? (
                pendingTasks.map((task) => (
                  <div key={task.id} className="flex items-start space-x-3 p-2 rounded-lg hover:bg-muted/30 transition-colors">
                    <div className={`w-3 h-3 rounded-full mt-1.5 flex-shrink-0 ${getTaskPriorityColor(task.priority)}`}></div>
                    <div className="flex-1 min-w-0">
                      <p className="text-sm font-medium">{task.task}</p>
                      <p className="text-xs text-muted-foreground mt-1">Due: {task.due}</p>
                    </div>
                    <Button size="sm" variant="ghost" className="h-6 w-6 p-0 flex-shrink-0">
                      <ArrowRight className="h-3 w-3" />
                    </Button>
                  </div>
                ))
              ) : (
                <div className="flex items-center justify-center h-32">
                  <p className="text-sm text-muted-foreground">No pending tasks</p>
                </div>
              )}
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
