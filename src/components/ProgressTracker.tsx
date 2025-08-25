import { useState } from "react";
import { Badge } from "@/components/ui/badge";
import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import { Button } from "@/components/ui/button";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "@/components/ui/tooltip";
import { MoreVertical, Edit2 } from "lucide-react";

interface Candidate {
  id: number;
  name: string;
  email: string;
  phone?: string;
  appliedFor: string;
  status: number;
  created_at: string;
  skill_match_score?: number;
  interviews_count?: number;
  avg_prescreening_score?: number;
  max_prescreening_score?: number;
}

interface ProgressTrackerProps {
  candidates: Candidate[];
  onCandidateClick?: (candidate: Candidate) => void;
  onStatusChange?: (candidateId: number, newStatus: number) => void;
}

const PROGRESS_STAGES = [
  { id: 1, title: "New Candidates", status: 1, color: "bg-blue-100" },
  { id: 2, title: "Shortlisted", status: 2, color: "bg-yellow-100" },
  { id: 3, title: "Pre Screening Test", status: 3, color: "bg-orange-100" },
  { id: 4, title: "Technical Interview", status: [4, 5], color: "bg-purple-100" },
  { id: 5, title: "Round 2", status: 6, color: "bg-green-100" }
];


export default function ProgressTracker({
  candidates,
  onCandidateClick,
  onStatusChange
}: ProgressTrackerProps) {
  const getCandidatesByStatus = (status: number | number[]) => {
    if (Array.isArray(status)) {
      return candidates.filter(candidate => status.includes(candidate.status));
    }
    return candidates.filter(candidate => candidate.status === status);
  };

  const handleEdit = (candidate: Candidate) => {
    console.log('Edit candidate:', candidate.id);
  };

  // Get candidate scores based on status - using real database values
  const getCandidateScores = (candidate: Candidate) => {
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

  return (
    <div className="flex-1 flex flex-col overflow-hidden">
      {/* Progress Header - Fixed */}
      <div className="flex items-center mb-6 flex-shrink-0">
        {PROGRESS_STAGES.map((stage, index) => {
          const count = getCandidatesByStatus(stage.status).length;

          return (
            <div key={stage.id} className="flex items-center">
              {/* Stage Box */}
              <div className="flex items-center justify-center bg-white border border-gray-200 rounded-lg px-4 py-3 shadow-sm" style={{ width: '200px' }}>
                <span className="text-sm font-medium text-gray-700 mr-2 text-center">
                  {stage.title}
                </span>
                {count > 0 && (
                  <Badge variant="secondary" className="bg-blue-500 text-white text-xs px-2 py-1">
                    {count}
                  </Badge>
                )}
              </div>
              
              {/* Triangle Arrow */}
              {index < PROGRESS_STAGES.length - 1 && (
                <div className="flex items-center mx-2">
                  <div className="w-0 h-0 border-l-[12px] border-l-white border-t-[12px] border-t-transparent border-b-[12px] border-b-transparent"></div>
                  <div className="w-4 h-0.5 bg-gray-300"></div>
                </div>
              )}
            </div>
          );
        })}
      </div>

      {/* Candidates Grid - Each Column Scrolls Individually */}
      <TooltipProvider>
        <div className="flex-1 flex gap-6 overflow-hidden">
          {PROGRESS_STAGES.map((stage) => {
            const stageCandidates = getCandidatesByStatus(stage.status);
            
            return (
              <div key={stage.id} className="flex-1 flex flex-col overflow-hidden">
                <div className={`${stage.color} rounded-lg p-4 h-full flex flex-col`}>
                  <div className="flex-1 overflow-y-auto hide-scrollbar space-y-3">
                    {stageCandidates.length === 0 ? (
                      <p className="text-center text-gray-500 text-sm py-8">No candidates</p>
                    ) : (
                      stageCandidates.map((candidate) => {
                        const candidateScores = getCandidateScores(candidate);
                        
                        return (
                          <Tooltip key={candidate.id}>
                            <TooltipTrigger asChild>
                              <div 
                                className="bg-white border border-gray-200 rounded-lg p-4 hover:shadow-md transition-shadow cursor-pointer"
                                onClick={() => onCandidateClick?.(candidate)}
                              >
                                <div className="flex items-center space-x-3">
                                  <Avatar className="h-10 w-10 flex-shrink-0">
                                    <AvatarFallback className={`${(() => {
                                      const colors = [
                                        'bg-blue-500', 'bg-purple-500', 'bg-green-500',
                                        'bg-orange-500', 'bg-pink-500', 'bg-indigo-500'
                                      ];
                                      const initials = candidate.name.split(' ').map(n => n[0]).join('').toUpperCase().slice(0, 2);
                                      const index = initials.charCodeAt(0) % colors.length;
                                      return colors[index];
                                    })()} text-white text-sm font-bold`}>
                                      {candidate.name.split(' ').map(n => n[0]).join('').toUpperCase().slice(0, 2)}
                                    </AvatarFallback>
                                  </Avatar>
                                  <div className="flex-1 min-w-0">
                                    <h4 className="text-sm font-semibold text-gray-900 truncate">
                                      {candidate.name}
                                    </h4>
                                    <p className="text-xs text-gray-500 truncate" title={candidate.email}>
                                      {candidate.email}
                                    </p>
                                  </div>
                                </div>
                              </div>
                            </TooltipTrigger>
                            <TooltipContent side="top" className="p-3 max-w-xs">
                              <div className="space-y-2">
                                <div className="font-medium text-sm">{candidate.name}</div>
                                <div className="text-xs text-muted-foreground">{candidate.email}</div>
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
                        );
                      })
                    )}
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      </TooltipProvider>
    </div>
  );
}
