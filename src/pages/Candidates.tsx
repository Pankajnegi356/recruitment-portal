import { useState, useEffect } from "react";
import { Plus, RefreshCw, List, Calendar, ArrowLeft, Edit, Trash2, MoreHorizontal } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { Badge } from "@/components/ui/badge";
import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "@/components/ui/tooltip";
import {
  Dialog,
  DialogContent,
  DialogTrigger,
} from "@/components/ui/dialog";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from "@/components/ui/alert-dialog";
import { getCandidates, getCandidateById, deleteCandidate } from "../services/api.js";
import { getStatusLabel, getStatusColor } from "../config/database.js";
import ProgressTracker from "@/components/ProgressTracker";
import CandidateForm from "../components/forms/CandidateForm.tsx";


export default function Candidates() {
  const [viewMode, setViewMode] = useState<"list" | "timeline">("list");
  const [selectedCandidate, setSelectedCandidate] = useState<number | null>(null);
  const [candidates, setCandidates] = useState<any[]>([]);
  const [candidateDetails, setCandidateDetails] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [showCreateForm, setShowCreateForm] = useState(false);
  const [editingCandidate, setEditingCandidate] = useState<any>(null);
  const [deleteCandidate_, setDeleteCandidate_] = useState<any>(null);

  // Fetch candidates on component mount
  useEffect(() => {
    const fetchCandidates = async () => {
      try {
        setLoading(true);
        const data = await getCandidates();
        setCandidates(data);
      } catch (error) {
        console.error('Failed to fetch candidates:', error);
      } finally {
        setLoading(false);
      }
    };

    fetchCandidates();
  }, []);

  // Fetch candidate details when selected
  useEffect(() => {
    const fetchCandidateDetails = async () => {
      if (selectedCandidate) {
        try {
          const details = await getCandidateById(selectedCandidate);
          setCandidateDetails(details);
        } catch (error) {
          console.error('Failed to fetch candidate details:', error);
        }
      }
    };

    fetchCandidateDetails();
  }, [selectedCandidate]);

  // Refresh data function
  const handleRefresh = async () => {
    try {
      setLoading(true);
      const data = await getCandidates();
      setCandidates(data);
    } catch (error) {
      console.error('Failed to refresh candidates:', error);
    } finally {
      setLoading(false);
    }
  };

  // Get avatar initials from name
  const getAvatarInitials = (name: string) => {
    return name.split(' ').map(n => n[0]).join('').toUpperCase();
  };

  // Format date for display
  const formatDate = (dateString: string) => {
    const date = new Date(dateString);
    // Add 5 hours to convert UTC to IST
    date.setHours(date.getHours() + 5);
    return date.toLocaleDateString();
  };

  // Helper function to calculate time ago (same as Activity page)
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

  // Generate candidate history in activity feed format
  const getCandidateHistory = (candidate: any) => {
    if (!candidate) return [];
    
    const appliedDate = new Date(candidate.created_at);
    const history = [];
    
    // Application submitted (always show this first)
    history.push({
      title: `${candidate.name} applied for ${candidate.position_applied || candidate.job_title || candidate.appliedFor || 'General Application'}`,
      timestamp: getTimeAgo(appliedDate),
      icon: '👤',
      type: 'application'
    });
    
    // For rejected candidates, we need to show their progression before rejection
    // We'll assume they went through stages based on their previous status or show a typical flow
    const isRejected = candidate.status === 0;
    const maxStatusReached = isRejected ? (candidate.max_status_reached || 5) : candidate.status;
    
    // Show progression based on max status reached (for rejected) or current status
    const statusToCheck = isRejected ? maxStatusReached : candidate.status;
    
    if (statusToCheck >= 2) {
      history.push({
        title: `${candidate.name} moved to Shortlisted stage`,
        timestamp: getTimeAgo(appliedDate),
        icon: '✅',
        type: 'status_change'
      });
    }
    
    if (statusToCheck >= 3) {
      history.push({
        title: `${candidate.name} moved to Pre-screening Test stage`,
        timestamp: getTimeAgo(appliedDate),
        icon: '📝', 
        type: 'status_change'
      });
    }
    
    if (statusToCheck >= 4) {
      history.push({
        title: `${candidate.name} moved to Negotiating Interview Date stage`,
        timestamp: getTimeAgo(appliedDate),
        icon: '📅',
        type: 'status_change'
      });
    }
    
    if (statusToCheck >= 5) {
      history.push({
        title: `${candidate.name} moved to Interview Confirmed stage`,
        timestamp: getTimeAgo(appliedDate),
        icon: '🎯',
        type: 'status_change'
      });
    }
    
    if (statusToCheck >= 6) {
      history.push({
        title: `${candidate.name} cleared interview - moved to Round 2`,
        timestamp: getTimeAgo(appliedDate),
        icon: '🏆',
        type: 'status_change'
      });
    }
    
    // Handle rejection status (0) - show this as the final step
    if (isRejected) {
      history.push({
        title: `${candidate.name} was rejected`,
        timestamp: getTimeAgo(appliedDate),
        icon: '❌',
        type: 'rejection'
      });
    }
    
    // Reverse to show newest on top, oldest at bottom (newest first)
    return history.reverse();
  };

  // Get candidate scores based on status
  const getCandidateScores = (candidate: any) => {
    const scores = [];
    
    // Skill Match Score from database (candidates.skill_match_score)
    if (candidate.skill_match_score) {
      scores.push({
        label: 'Skill Match',
        value: Math.round(candidate.skill_match_score * 100),
        color: 'text-blue-600'
      });
    }
    
    // Pre-screening score from interview_tests table (test_score out of max_score = 25)
    // Show if candidate is in pre-screening stage (status 3) or beyond, and has a score
    if (candidate.status >= 3 && candidate.avg_prescreening_score && candidate.avg_prescreening_score > 0) {
      // Convert score out of 25 to percentage (e.g., 16/25 = 64%)
      const percentage = Math.round((candidate.avg_prescreening_score / 25) * 100);
      scores.push({
        label: 'Pre-screening',
        value: percentage,
        color: 'text-orange-600'
      });
    }
    
    return scores;
  };

  // Handle status change for drag-and-drop
  const handleStatusChange = (candidateId: number, newStatus: number) => {
    setCandidates(prevCandidates => 
      prevCandidates.map(candidate => 
        candidate.id === candidateId 
          ? { ...candidate, status: newStatus } 
          : candidate
      )
    );
    console.log(`Candidate ${candidateId} status changed to ${newStatus}`);
  };

  // Handle candidate click from progress tracker
  const handleCandidateClick = (candidate: any) => {
    setSelectedCandidate(candidate.id);
  };

  // Handle form submit (create or update)
  const handleFormSubmit = async (candidateData: any) => {
    try {
      await handleRefresh(); // Refresh the list
      setShowCreateForm(false);
      setEditingCandidate(null);
    } catch (error) {
      console.error('Failed to save candidate:', error);
    }
  };

  // Handle edit candidate
  const handleEditCandidate = (candidate: any) => {
    setEditingCandidate(candidate);
  };

  // Handle delete candidate
  const handleDeleteCandidate = async () => {
    if (!deleteCandidate_) return;
    
    try {
      await deleteCandidate(deleteCandidate_.id);
      await handleRefresh(); // Refresh the list
      setDeleteCandidate_(null);
    } catch (error) {
      console.error('Failed to delete candidate:', error);
    }
  };

  // Candidate detail view
  if (selectedCandidate && candidateDetails) {
    return (
      <div className="space-y-6">
        {/* Header */}
        <div className="flex items-center space-x-4">
          <Button 
            variant="ghost" 
            size="sm"
            onClick={() => {
              setSelectedCandidate(null);
              setCandidateDetails(null);
            }}
            className="flex items-center space-x-2"
          >
            <ArrowLeft className="h-4 w-4" />
            <span>Back to Candidates</span>
          </Button>
        </div>

        {/* Candidate Profile */}
        <div className="flex items-center space-x-4">
          <Avatar className="h-16 w-16">
            <AvatarFallback className="bg-green-600 text-white text-lg">
              {getAvatarInitials(candidateDetails.name)}
            </AvatarFallback>
          </Avatar>
          <div>
            <h1 className="text-2xl font-bold text-foreground">{candidateDetails.name}</h1>
            <p className="text-muted-foreground">{getStatusLabel(candidateDetails.status)}</p>
          </div>
        </div>

        {/* Tabs */}
        <Tabs defaultValue="summary" className="w-full">
          <TabsList className="grid w-full grid-cols-4">
            <TabsTrigger value="summary">Summary</TabsTrigger>
            <TabsTrigger value="resume">Resume</TabsTrigger>
            <TabsTrigger value="status">Status</TabsTrigger>
            <TabsTrigger value="history">History</TabsTrigger>
          </TabsList>
          
          <TabsContent value="summary" className="mt-6">
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
              {/* Candidate Details */}
              <Card>
                <CardHeader>
                  <CardTitle>Candidate Details</CardTitle>
                </CardHeader>
                <CardContent className="space-y-3">
                  <div className="flex items-center">
                    <span className="font-medium mr-2">Full Name:</span>
                    <span className="text-muted-foreground">{candidateDetails.name}</span>
                  </div>
                  <div className="flex items-center">
                    <span className="font-medium mr-2">Email Address:</span>
                    <span className="text-muted-foreground">{candidateDetails.email}</span>
                  </div>
                  <div className="flex items-center">
                    <span className="font-medium mr-2">Phone Number:</span>
                    <span className="text-muted-foreground">{candidateDetails.phone || 'Not provided'}</span>
                  </div>
                  <div className="flex items-center">
                    <span className="font-medium mr-2">Applied For:</span>
                    <span className="text-muted-foreground">{candidateDetails.position_applied || candidateDetails.job_title || 'General Application'}</span>
                  </div>
                  {candidateDetails.experience_years && (
                    <div className="flex items-center">
                      <span className="font-medium mr-2">Experience:</span>
                      <span className="text-muted-foreground">{candidateDetails.experience_years} years</span>
                    </div>
                  )}
                  <div className="flex items-center">
                    <span className="font-medium mr-2">Skill Match Score:</span>
                    <span className="text-muted-foreground">{candidateDetails.skill_match_score}%</span>
                  </div>
                  {candidateDetails.avg_prescreening_score && (
                    <div className="flex items-center">
                      <span className="font-medium mr-2">Prescreening Score:</span>
                      <span className="text-muted-foreground">{candidateDetails.avg_prescreening_score}/25 ({Math.round((candidateDetails.avg_prescreening_score / 25) * 100)}%)</span>
                    </div>
                  )}
                  {candidateDetails.avg_interview_rating && (
                    <div className="flex items-center">
                      <span className="font-medium mr-2">Interview Rating:</span>
                      <span className="text-muted-foreground">{candidateDetails.avg_interview_rating}/10</span>
                    </div>
                  )}
                  <div className="flex items-center">
                    <span className="font-medium mr-2">Application Date:</span>
                    <span className="text-muted-foreground">{formatDate(candidateDetails.created_at)}</span>
                  </div>
                </CardContent>
              </Card>

              {/* Candidate Summary */}
              <Card>
                <CardHeader>
                  <CardTitle>Candidate Summary</CardTitle>
                </CardHeader>
                <CardContent>
                  <p className="text-sm text-muted-foreground leading-relaxed">
                    {candidateDetails.summary || 'No summary available.'}
                  </p>
                </CardContent>
              </Card>
            </div>
          </TabsContent>
          
          <TabsContent value="resume" className="mt-6">
            <Card>
              <CardHeader>
                <div className="flex items-center justify-between">
                  <CardTitle>Resume</CardTitle>
                  {candidateDetails.resume_path && (
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => window.open(candidateDetails.resume_path, '_blank')}
                      className="flex items-center space-x-2"
                    >
                      <svg className="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 10v6m0 0l-3-3m3 3l3-3m2 8H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                      </svg>
                      <span>Download</span>
                    </Button>
                  )}
                </div>
              </CardHeader>
              <CardContent className="p-0">
                {candidateDetails.resume_path ? (
                  <div className="w-full h-[600px]">
                    <iframe
                      src={candidateDetails.resume_path.includes('drive.google.com') 
                        ? candidateDetails.resume_path.replace('/view?usp=sharing', '/preview')
                        : candidateDetails.resume_path}
                      className="w-full h-full border-0 rounded-b-lg"
                      title="Resume Preview"
                    />
                  </div>
                ) : (
                  <div className="p-8 text-center">
                    <p className="text-muted-foreground">No resume uploaded</p>
                  </div>
                )}
              </CardContent>
            </Card>
          </TabsContent>
          
          <TabsContent value="status" className="mt-6">
            <div className="space-y-6">
              {/* Progress Header - Fixed */}
              <div className="flex items-center mb-6 flex-shrink-0">
                {[1, 2, 3, 4].map((stageStatus, index) => {
                  const stageLabels = ['New Candidates', 'Shortlisted', 'Pre Screening Test', 'Technical Interview'];
                  const isActive = candidateDetails.status === stageStatus;
                  const isCompleted = candidateDetails.status > stageStatus;
                  
                  return (
                    <div key={stageStatus} className="flex items-center">
                      {/* Stage Box */}
                      <div className={`flex items-center justify-center border rounded-lg px-4 py-3 shadow-sm ${
                        isActive ? 'bg-blue-100 border-blue-300' : 
                        isCompleted ? 'bg-green-100 border-green-300' : 
                        'bg-white border-gray-200'
                      }`} style={{ width: '200px' }}>
                        <span className={`text-sm font-medium text-center ${
                          isActive ? 'text-blue-700' : 
                          isCompleted ? 'text-green-700' : 
                          'text-gray-700'
                        }`}>
                          {stageLabels[index]}
                        </span>
                        {isActive && (
                          <Badge variant="secondary" className="bg-blue-500 text-white text-xs px-2 py-1 ml-2">
                            Current
                          </Badge>
                        )}
                      </div>
                      
                      {/* Triangle Arrow */}
                      {index < 3 && (
                        <div className="flex items-center mx-2">
                          <div className="w-0 h-0 border-l-[12px] border-l-white border-t-[12px] border-t-transparent border-b-[12px] border-b-transparent"></div>
                          <div className="w-4 h-0.5 bg-gray-300"></div>
                        </div>
                      )}
                    </div>
                  );
                })}
              </div>

              {/* Single Candidate in Appropriate Column */}
              <TooltipProvider>
                <div className="flex gap-6">
                  {[1, 2, 3, 4].map((stageStatus) => {
                    const stageLabels = ['New Candidates', 'Shortlisted', 'Pre Screening Test', 'Technical Interview'];
                    const stageColors = ['bg-blue-100', 'bg-yellow-100', 'bg-orange-100', 'bg-purple-100'];
                    const isCurrentStage = candidateDetails.status === stageStatus;
                    const candidateScores = getCandidateScores(candidateDetails);
                    
                    return (
                      <div key={stageStatus} className="flex-1">
                        <div className={`${stageColors[stageStatus - 1]} rounded-lg p-4 h-32 flex flex-col`}>
                          {isCurrentStage ? (
                            <Tooltip>
                              <TooltipTrigger asChild>
                                <div className="bg-white border border-gray-200 rounded-lg p-4 hover:shadow-md transition-shadow cursor-pointer">
                                  <div className="flex items-center space-x-3">
                                    <Avatar className="h-10 w-10 flex-shrink-0">
                                      <AvatarFallback className="bg-green-600 text-white text-sm font-bold">
                                        {getAvatarInitials(candidateDetails.name)}
                                      </AvatarFallback>
                                    </Avatar>
                                    <div className="flex-1 min-w-0">
                                      <h4 className="text-sm font-semibold text-gray-900 truncate">
                                        {candidateDetails.name}
                                      </h4>
                                      <p className="text-xs text-gray-500 truncate" title={candidateDetails.email}>
                                        {candidateDetails.email}
                                      </p>
                                    </div>
                                  </div>
                                </div>
                              </TooltipTrigger>
                              <TooltipContent side="top" className="p-3 max-w-xs">
                                <div className="space-y-2">
                                  <div className="font-medium text-sm">{candidateDetails.name}</div>
                                  <div className="text-xs text-muted-foreground">{candidateDetails.email}</div>
                                  {candidateScores.length > 0 && (
                                    <div className="space-y-1 mt-2">
                                      <div className="text-xs font-medium">Scores:</div>
                                      {candidateScores.map((score, index) => (
                                        <div key={index} className="flex justify-between items-center">
                                          <span className="text-xs">{score.label}:</span>
                                          <span className={`text-xs font-medium ${score.color}`}>{score.value}%</span>
                                        </div>
                                      ))}
                                    </div>
                                  )}
                                </div>
                              </TooltipContent>
                            </Tooltip>
                          ) : (
                            <p className="text-center text-gray-500 text-sm py-8">No candidates</p>
                          )}
                        </div>
                      </div>
                    );
                  })}
                </div>
              </TooltipProvider>
            </div>
          </TabsContent>
          
          <TabsContent value="history" className="mt-6">
            <Card>
              <CardHeader>
                <CardTitle>Application History</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="space-y-3">
                  {getCandidateHistory(candidateDetails).map((historyItem, index) => (
                    <div key={index} className="flex items-start space-x-3 p-3 hover:bg-muted/30 rounded-lg transition-colors">
                      <div className="text-lg">{historyItem.icon}</div>
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center justify-between">
                          <p className="text-sm font-medium text-foreground truncate">
                            {historyItem.title}
                          </p>
                          <span className="text-xs text-muted-foreground flex-shrink-0 ml-2">
                            {historyItem.timestamp}
                          </span>
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              </CardContent>
            </Card>
          </TabsContent>
        </Tabs>
      </div>
    );
  }

  return (
    <div className="h-full flex flex-col">
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-bold text-foreground">Candidates</h1>
        <div className="flex items-center space-x-3">
          <div className="flex items-center border rounded-lg">
            <Button
              variant={viewMode === "list" ? "default" : "ghost"}
              size="sm"
              onClick={() => setViewMode("list")}
              className="rounded-r-none"
            >
              <List className="h-4 w-4" />
            </Button>
            <Button
              variant={viewMode === "timeline" ? "default" : "ghost"}
              size="sm"
              onClick={() => setViewMode("timeline")}
              className="rounded-l-none"
            >
              <Calendar className="h-4 w-4" />
            </Button>
          </div>
          <Button variant="outline" size="sm" className="flex items-center space-x-2" onClick={handleRefresh} disabled={loading}>
            <RefreshCw className={`h-4 w-4 ${loading ? 'animate-spin' : ''}`} />
            <span>Refresh</span>
          </Button>
        </div>
      </div>

      {/* Add Candidates Button */}
      <div className="mb-6">
        <Dialog open={showCreateForm} onOpenChange={setShowCreateForm}>
          <DialogTrigger asChild>
            <Button className="flex items-center space-x-2" data-create-candidate>
              <Plus className="h-4 w-4" />
              <span>Add Candidate</span>
            </Button>
          </DialogTrigger>
          <DialogContent className="max-w-3xl">
            <CandidateForm
              onSubmit={handleFormSubmit}
              onCancel={() => setShowCreateForm(false)}
            />
          </DialogContent>
        </Dialog>
      </div>

      {viewMode === "list" ? (
        /* List View with Fixed Headers */
        <div className="flex-1 overflow-hidden">
          <Card className="h-full flex flex-col">
            {/* Fixed Header */}
            <div className="bg-muted/50 border-b border-border p-0 flex-shrink-0">
              <div className="grid grid-cols-5 gap-4 p-4 font-semibold text-sm">
                <div>Candidate Name</div>
                <div>Applied for</div>
                <div>Department</div>
                <div>Status</div>
                <div>Applied date</div>
              </div>
            </div>
            
            {/* Scrollable Content */}
            <div className="flex-1 overflow-y-auto hide-scrollbar">
              <div className="divide-y divide-border">
                {candidates.map((candidate) => (
                  <div 
                    key={candidate.id} 
                    className="grid grid-cols-5 gap-4 p-4 hover:bg-muted/50 transition-colors cursor-pointer"
                    onClick={() => setSelectedCandidate(candidate.id)}
                  >
                    <div className="font-medium text-primary hover:underline">
                      {candidate.name}
                    </div>
                    <div className="text-sm text-muted-foreground">
                      {candidate.position_applied || candidate.job_title || 'General Application'}
                    </div>
                    <div className="text-sm text-muted-foreground">
                      {candidate.department_name || 'N/A'}
                    </div>
                    <div>
                      <Badge className={getStatusColor(candidate.status)}>
                        {getStatusLabel(candidate.status)}
                      </Badge>
                    </div>
                    <div className="text-sm text-muted-foreground">
                      {formatDate(candidate.created_at)}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </Card>
        </div>
      ) : (
        /* Progress Tracker View */
        loading ? (
          <div className="flex justify-center items-center py-12">
            <RefreshCw className="h-8 w-8 animate-spin" />
            <span className="ml-2 text-muted-foreground">Loading candidates...</span>
          </div>
        ) : (
          <ProgressTracker 
            candidates={candidates}
            onCandidateClick={handleCandidateClick}
            onStatusChange={handleStatusChange}
          />
        )
      )}

      {/* Edit Dialog */}
      <Dialog open={!!editingCandidate} onOpenChange={(open) => !open && setEditingCandidate(null)}>
        <DialogContent className="max-w-3xl">
          {editingCandidate && (
            <CandidateForm
              candidate={editingCandidate}
              onSubmit={handleFormSubmit}
              onCancel={() => setEditingCandidate(null)}
            />
          )}
        </DialogContent>
      </Dialog>

      {/* Delete Confirmation Dialog */}
      <AlertDialog open={!!deleteCandidate_} onOpenChange={(open) => !open && setDeleteCandidate_(null)}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Are you sure?</AlertDialogTitle>
            <AlertDialogDescription>
              This action cannot be undone. This will permanently delete the candidate
              {deleteCandidate_ && ` "${deleteCandidate_.name}"`} and all associated data.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Cancel</AlertDialogCancel>
            <AlertDialogAction onClick={handleDeleteCandidate} className="bg-red-600 hover:bg-red-700">
              Delete
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  );
}
