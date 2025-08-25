import { useState, useEffect } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { ArrowLeft, Users, UserCheck, Building, Calendar, Mail, Phone, Edit, Trash2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import {
  Dialog,
  DialogContent,
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
import DepartmentForm from "../components/forms/DepartmentForm.tsx";

export default function DepartmentDetail() {
  const { id } = useParams();
  const navigate = useNavigate();
  const [department, setDepartment] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [showEditForm, setShowEditForm] = useState(false);

  // Fetch department details
  useEffect(() => {
    const fetchDepartment = async () => {
      try {
        setLoading(true);
        const response = await fetch(`/api/departments/${id}`, {
          headers: {
            'Authorization': `Bearer ${localStorage.getItem('auth_token')}`
          }
        });
        
        if (response.ok) {
          const data = await response.json();
          setDepartment(data);
        } else {
          console.error('Failed to fetch department');
          navigate('/departments');
        }
      } catch (error) {
        console.error('Error fetching department:', error);
        navigate('/departments');
      } finally {
        setLoading(false);
      }
    };

    if (id) {
      fetchDepartment();
    }
  }, [id, navigate]);

  // Handle edit department
  const handleEditFormSubmit = async (departmentData: any) => {
    try {
      // Refresh department data
      const response = await fetch(`/api/departments/${id}`, {
        headers: {
          'Authorization': `Bearer ${localStorage.getItem('auth_token')}`
        }
      });
      
      if (response.ok) {
        const data = await response.json();
        setDepartment(data);
      }
      
      setShowEditForm(false);
    } catch (error) {
      console.error('Failed to refresh department:', error);
    }
  };

  // Handle delete department
  const handleDeleteDepartment = async () => {
    try {
      const response = await fetch(`/api/departments/${id}`, {
        method: 'DELETE',
        headers: {
          'Authorization': `Bearer ${localStorage.getItem('auth_token')}`
        }
      });

      if (response.ok) {
        navigate('/departments');
      } else {
        const error = await response.json();
        console.error('Failed to delete department:', error);
        alert('Failed to delete department: ' + (error.error || 'Unknown error'));
      }
    } catch (error) {
      console.error('Error deleting department:', error);
      alert('Network error. Please try again.');
    }
  };

  // Format date for display
  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'long',
      day: 'numeric'
    });
  };

  if (loading) {
    return (
      <div className="flex justify-center items-center h-64">
        <p className="text-muted-foreground">Loading department details...</p>
      </div>
    );
  }

  if (!department) {
    return (
      <div className="flex justify-center items-center h-64">
        <p className="text-muted-foreground">Department not found</p>
      </div>
    );
  }

  return (
    <div className="h-full flex flex-col space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center space-x-4">
          <Button
            variant="outline"
            size="sm"
            onClick={() => navigate('/departments')}
            className="flex items-center space-x-2"
          >
            <ArrowLeft className="h-4 w-4" />
            <span>Back to Departments</span>
          </Button>
          <div>
            <h1 className="text-3xl font-bold text-foreground">{department.name}</h1>
            <p className="text-muted-foreground">Department Details</p>
          </div>
        </div>
        <div className="flex items-center space-x-2">
          <Button
            variant="outline"
            onClick={() => setShowEditForm(true)}
            className="flex items-center space-x-2 text-blue-600 hover:text-blue-700 hover:bg-blue-50"
          >
            <Edit className="h-4 w-4" />
            <span>Edit Department</span>
          </Button>
          <AlertDialog>
            <AlertDialogTrigger asChild>
              <Button
                variant="outline"
                className="flex items-center space-x-2 text-red-600 hover:text-red-700 hover:bg-red-50"
              >
                <Trash2 className="h-4 w-4" />
                <span>Delete</span>
              </Button>
            </AlertDialogTrigger>
            <AlertDialogContent>
              <AlertDialogHeader>
                <AlertDialogTitle>Delete Department</AlertDialogTitle>
                <AlertDialogDescription>
                  Are you sure you want to delete the "{department.name}" department? 
                  This action cannot be undone and will remove all associated data.
                </AlertDialogDescription>
              </AlertDialogHeader>
              <AlertDialogFooter>
                <AlertDialogCancel>Cancel</AlertDialogCancel>
                <AlertDialogAction
                  onClick={handleDeleteDepartment}
                  className="bg-red-600 hover:bg-red-700"
                >
                  Delete
                </AlertDialogAction>
              </AlertDialogFooter>
            </AlertDialogContent>
          </AlertDialog>
        </div>
      </div>

      {/* Department Overview Cards */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
        <Card>
          <CardContent className="p-6">
            <div className="flex items-center space-x-2">
              <Users className="h-8 w-8 text-blue-500" />
              <div>
                <p className="text-2xl font-bold">
                  {(department.team_members ? department.team_members.length : 0) + (department.manager_name ? 1 : 0)}
                </p>
                <p className="text-sm text-muted-foreground">Total Members</p>
              </div>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="p-6">
            <div className="flex items-center space-x-2">
              <UserCheck className="h-8 w-8 text-green-500" />
              <div>
                <p className="text-2xl font-bold">
                  {(department.team_members ? 
                    department.team_members.filter((m: any) => m.is_active).length : 0) + 
                    (department.manager_name ? 1 : 0)}
                </p>
                <p className="text-sm text-muted-foreground">Active Members</p>
              </div>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="p-6">
            <div className="flex items-center space-x-2">
              <Building className="h-8 w-8 text-amber-500" />
              <div>
                <p className="text-2xl font-bold">{department.manager_name ? 1 : 0}</p>
                <p className="text-sm text-muted-foreground">Manager Assigned</p>
              </div>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="p-6">
            <div className="flex items-center space-x-2">
              <Calendar className="h-8 w-8 text-purple-500" />
              <div>
                <p className="text-2xl font-bold">{formatDate(department.created_at).split(',')[0]}</p>
                <p className="text-sm text-muted-foreground">Created</p>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Department Information and Team */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Department Details */}
        <Card className="lg:col-span-2">
          <CardHeader>
            <CardTitle>Department Information</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div>
              <h3 className="font-semibold text-sm text-muted-foreground uppercase tracking-wide">Department Name</h3>
              <p className="text-lg font-medium">{department.name}</p>
            </div>
            
            {department.description && (
              <div>
                <h3 className="font-semibold text-sm text-muted-foreground uppercase tracking-wide">Description</h3>
                <p className="text-sm">{department.description}</p>
              </div>
            )}
            
            <div>
              <h3 className="font-semibold text-sm text-muted-foreground uppercase tracking-wide">Created Date</h3>
              <p className="text-sm">{formatDate(department.created_at)}</p>
            </div>
          </CardContent>
        </Card>

        {/* Department Team (Manager + Team Members) */}
        <Card>
          <CardHeader>
            <CardTitle>Department Team</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            {/* Department Manager First */}
            {department.manager_name ? (
              <div className="border rounded-lg p-3 hover:bg-muted/50 transition-colors bg-blue-50/50">
                <div className="flex items-center space-x-3">
                  <Avatar className="h-10 w-10">
                    <AvatarFallback className="bg-blue-500 text-white">
                      {department.manager_name.charAt(0).toUpperCase()}
                    </AvatarFallback>
                  </Avatar>
                  <div className="flex-1">
                    <p className="font-medium text-sm">{department.manager_name}</p>
                    <Badge variant="default" className="text-xs bg-blue-600 mt-1">
                      Manager
                    </Badge>
                    {department.manager_email && (
                      <div className="flex items-center space-x-1 mt-1">
                        <Mail className="h-3 w-3 text-muted-foreground" />
                        <p className="text-xs text-muted-foreground">{department.manager_email}</p>
                      </div>
                    )}
                  </div>
                </div>
              </div>
            ) : null}

            {/* Team Members */}
            {department.team_members && department.team_members.length > 0 ? (
              department.team_members.map((member: any) => (
                <div key={member.id} className="border rounded-lg p-3 hover:bg-muted/50 transition-colors">
                  <div className="flex items-center space-x-3">
                    <Avatar className="h-10 w-10">
                      <AvatarFallback className="bg-green-500 text-white">
                        {member.first_name?.charAt(0).toUpperCase()}{member.last_name?.charAt(0).toUpperCase()}
                      </AvatarFallback>
                    </Avatar>
                    <div className="flex-1">
                      <p className="font-medium text-sm">{member.first_name} {member.last_name}</p>
                      <div className="flex items-center space-x-1 mt-1">
                        <Badge variant="secondary" className="text-xs capitalize">
                          {member.role}
                        </Badge>
                        <Badge 
                          variant={member.is_active ? "default" : "destructive"}
                          className="text-xs"
                        >
                          {member.is_active ? 'Active' : 'Inactive'}
                        </Badge>
                      </div>
                      <div className="flex items-center space-x-1 mt-1">
                        <Mail className="h-3 w-3 text-muted-foreground" />
                        <p className="text-xs text-muted-foreground">{member.email}</p>
                      </div>
                    </div>
                  </div>
                </div>
              ))
            ) : null}

            {/* Empty state when no manager and no team members */}
            {!department.manager_name && (!department.team_members || department.team_members.length === 0) && (
              <div className="text-center py-8">
                <Users className="h-12 w-12 text-muted-foreground mx-auto mb-2" />
                <p className="text-sm font-medium text-muted-foreground">No team assigned</p>
                <p className="text-xs text-muted-foreground">Use edit to assign team</p>
              </div>
            )}
          </CardContent>
        </Card>
      </div>

      {/* Edit Department Dialog */}
      <Dialog open={showEditForm} onOpenChange={setShowEditForm}>
        <DialogContent className="max-w-2xl">
          <DepartmentForm
            department={department}
            onSubmit={handleEditFormSubmit}
            onCancel={() => setShowEditForm(false)}
          />
        </DialogContent>
      </Dialog>
    </div>
  );
}
