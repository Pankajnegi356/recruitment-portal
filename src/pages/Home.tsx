import { useState, useEffect, useMemo } from "react";
import { Plus, Bell, TrendingUp, Users, Briefcase, Activity, BarChart3 } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar";
import { PieChart, Pie, Cell, ResponsiveContainer, Legend, Tooltip } from "recharts";
import { getDashboardStats, getCandidates, getJobs } from "../services/api.js";

export default function Home() {
  const [dashboardStats, setDashboardStats] = useState<any>(null);
  const [recentCandidates, setRecentCandidates] = useState<any[]>([]);
  const [recentJobs, setRecentJobs] = useState<any[]>([]);
  const [allJobs, setAllJobs] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [screenWidth, setScreenWidth] = useState(typeof window !== 'undefined' ? window.innerWidth : 1024);

  // Fetch dashboard data on component mount
  useEffect(() => {
    const fetchDashboardData = async () => {
      try {
        setLoading(true);
        const [stats, candidates, jobs] = await Promise.all([
          getDashboardStats(),
          getCandidates(),
          getJobs()
        ]);
        setDashboardStats(stats);
        // Store all jobs for pie chart
        setAllJobs(jobs);
        // Get most recent items only
        setRecentCandidates(candidates.slice(0, 5)); // Get 5 most recent candidates
        setRecentJobs(jobs.slice(0, 5)); // Get 5 most recent jobs
      } catch (error) {
        console.error('Failed to fetch dashboard data:', error);
      } finally {
        setLoading(false);
      }
    };

    fetchDashboardData();
  }, []);

  // Get avatar initials from name
  const getAvatarInitials = (name: string) => {
    return name.split(' ').map(n => n[0]).join('').toUpperCase();
  };

  // Generate consistent colors for avatars based on name
  const getAvatarColor = (name: string) => {
    const colors = [
      'bg-red-500 text-white',
      'bg-blue-500 text-white', 
      'bg-green-500 text-white',
      'bg-yellow-500 text-white',
      'bg-purple-500 text-white',
      'bg-pink-500 text-white',
      'bg-indigo-500 text-white',
      'bg-orange-500 text-white'
    ];
    
    // Create a simple hash from the name to get consistent colors
    let hash = 0;
    for (let i = 0; i < name.length; i++) {
      hash = name.charCodeAt(i) + ((hash << 5) - hash);
    }
    return colors[Math.abs(hash) % colors.length];
  };

  // Get job initials with colors
  const getJobInitials = (title: string) => {
    return title.split(' ').map((word: string) => word[0]).join('').slice(0, 2).toUpperCase();
  };

  // Generate colors for job badges
  const getJobColor = (title: string) => {
    const colors = [
      'bg-blue-500 text-white',
      'bg-green-500 text-white',
      'bg-purple-500 text-white', 
      'bg-orange-500 text-white',
      'bg-pink-500 text-white',
      'bg-teal-500 text-white'
    ];
    
    let hash = 0;
    for (let i = 0; i < title.length; i++) {
      hash = title.charCodeAt(i) + ((hash << 5) - hash);
    }
    return colors[Math.abs(hash) % colors.length];
  };

  // Memoized pie chart data to prevent re-renders
  const pieChartData = useMemo(() => {
    if (!allJobs || allJobs.length === 0) return [];
    
    try {
      const statusCounts = allJobs.reduce((acc: any, job: any) => {
        const status = job?.status || 'Unknown';
        acc[status] = (acc[status] || 0) + 1;
        return acc;
      }, {});

      const chartData = Object.entries(statusCounts).map(([status, count]) => ({
        name: status,
        value: count as number
      }));

      return chartData;
    } catch (error) {
      console.error('Error generating pie chart data:', error);
      return [];
    }
  }, [allJobs]);

  // Colors for pie chart segments
  const PIE_COLORS = {
    'Active': '#10b981', // green-500
    'On Hold': '#f59e0b', // amber-500  
    'Completed': '#3b82f6', // blue-500
    'Canceled': '#ef4444' // red-500
  };

  return (
    <div className="space-y-4">
      <h1 className="text-xl font-bold text-foreground mb-4">Home</h1>

      {/* Dashboard Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4 auto-rows-fr">
        {/* Notifications */}
        <Card className="flex flex-col h-full">
          <CardHeader>
            <CardTitle className="flex items-center space-x-2">
              <Bell className="h-5 w-5" />
              <span>Notifications</span>
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-center py-4">
              <p className="text-muted-foreground text-sm">You don't have any notifications.</p>
              <p className="text-muted-foreground text-xs mt-2">
                Our alert system will let you know immediately once you receive a notification.
              </p>
              <p className="text-muted-foreground text-xs mt-1">
                Just keep an eye on the notifications icon at the top of your screen.
              </p>
            </div>
          </CardContent>
        </Card>

        {/* Top Performers */}
        <Card className="flex flex-col h-full">
          <CardHeader>
            <CardTitle className="flex items-center space-x-2">
              <TrendingUp className="h-5 w-5" />
              <span>Top Performers</span>
            </CardTitle>
          </CardHeader>
          <CardContent className="flex-1 flex items-center justify-center">
            <div className="text-center py-4">
              <p className="text-muted-foreground text-sm">There are no other users created yet.</p>
              <p className="text-muted-foreground text-xs mt-2">
                Here you will find the ranking of your team's performance.
              </p>
              <p className="text-muted-foreground text-xs mt-1">
                Based on hired candidates and jobs.
              </p>
              <p className="text-muted-foreground text-xs mt-1">
                Start creating users and then build your team.
              </p>
            </div>
          </CardContent>
        </Card>

        {/* Recent Actions */}
        <Card className="flex flex-col h-full">
          <CardHeader>
            <CardTitle className="flex items-center space-x-2">
              <Activity className="h-5 w-5" />
              <span>Recent Actions</span>
            </CardTitle>
          </CardHeader>
          <CardContent className="flex-1">
            <div className="space-y-6">
              {/* Candidates Section */}
              <div>
                <h4 className="font-semibold text-sm flex items-center space-x-2 mb-3">
                  <Users className="h-4 w-4" />
                  <span>CANDIDATES</span>
                </h4>
                <div className="flex items-center space-x-2">
                  {loading ? (
                    <p className="text-sm text-muted-foreground">Loading...</p>
                  ) : recentCandidates.length === 0 ? (
                    <p className="text-sm text-muted-foreground">No recent candidates</p>
                  ) : (
                    recentCandidates.map((candidate, index) => (
                      <Avatar key={index} className="h-10 w-10" title={candidate.name}>
                        <AvatarFallback className={`text-xs font-semibold ${getAvatarColor(candidate.name)}`}>
                          {getAvatarInitials(candidate.name)}
                        </AvatarFallback>
                      </Avatar>
                    ))
                  )}
                </div>
              </div>
              
              {/* Jobs Section */}
              <div>
                <h4 className="font-semibold text-sm flex items-center space-x-2 mb-3">
                  <Briefcase className="h-4 w-4" />
                  <span>JOBS</span>
                </h4>
                <div className="flex items-start space-x-3">
                  {loading ? (
                    <p className="text-sm text-muted-foreground">Loading...</p>
                  ) : recentJobs.length === 0 ? (
                    <p className="text-sm text-muted-foreground">No recent jobs</p>
                  ) : (
                    recentJobs.map((job, index) => (
                      <div key={index} className="bg-gray-50 rounded-lg p-3 flex flex-col items-center text-center" style={{ width: '80px' }} title={job.title}>
                        <div className={`w-10 h-10 rounded-full flex items-center justify-center mb-2 ${getJobColor(job.title)}`}>
                          <span className="text-xs font-semibold">
                            {getJobInitials(job.title)}
                          </span>
                        </div>
                        <div className="text-xs text-muted-foreground">
                          <div className="font-medium text-blue-600">{job.title.split(' ')[0]}</div>
                          <div className="text-gray-600">{job.title.split(' ').slice(1).join(' ')}</div>
                        </div>
                      </div>
                    ))
                  )}
                </div>
              </div>
            </div>
          </CardContent>
        </Card>

        {/* Reports */}
        <Card className="flex flex-col h-full">
          <CardHeader>
            <CardTitle className="flex items-center space-x-2">
              <BarChart3 className="h-5 w-5" />
              <span>Reports</span>
            </CardTitle>
          </CardHeader>
          <CardContent className="flex-1">
            {loading ? (
              <div className="flex items-center justify-center h-full">
                <p className="text-sm text-muted-foreground">Loading...</p>
              </div>
            ) : allJobs.length === 0 ? (
              <div className="flex items-center justify-center h-full">
                <div className="text-center">
                  <p className="text-muted-foreground text-sm">No jobs data available</p>
                </div>
              </div>
            ) : (
              <div className="h-full">
                <div className="mb-4">
                  <h4 className="font-semibold text-sm text-muted-foreground">JOB STATUS DISTRIBUTION</h4>
                  <p className="text-xs text-muted-foreground mt-1">Total Jobs: {allJobs.length}</p>
                </div>
                <div className="h-48">
                  {pieChartData.length > 0 ? (
                    <div className="h-full">
                      {/* Centered Pie Chart */}
                      <div className="h-36 mb-4">
                        <ResponsiveContainer width="100%" height="100%">
                          <PieChart>
                            <Pie
                              data={pieChartData}
                              cx="50%"
                              cy="50%"
                              innerRadius={0}
                              outerRadius={65}
                              paddingAngle={2}
                              dataKey="value"
                            >
                              {pieChartData.map((entry, index) => (
                                <Cell 
                                  key={`cell-${index}`} 
                                  fill={PIE_COLORS[entry.name as keyof typeof PIE_COLORS] || '#6b7280'} 
                                />
                              ))}
                            </Pie>
                          </PieChart>
                        </ResponsiveContainer>
                      </div>
                      
                      {/* Horizontal Legend Below */}
                      <div className="flex flex-wrap justify-center gap-4">
                        {pieChartData.map((entry, index) => (
                          <div key={index} className="flex items-center space-x-2">
                            <div 
                              className="w-3 h-3 rounded-sm" 
                              style={{ backgroundColor: PIE_COLORS[entry.name as keyof typeof PIE_COLORS] || '#6b7280' }}
                            ></div>
                            <span className="text-xs text-muted-foreground">{entry.name}</span>
                            <span className="text-xs font-medium">{entry.value}</span>
                          </div>
                        ))}
                      </div>
                    </div>
                  ) : (
                    <div className="flex items-center justify-center h-full">
                      <p className="text-sm text-muted-foreground">No chart data available</p>
                    </div>
                  )}
                </div>
              </div>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  );
}