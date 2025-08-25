import { useState, useEffect } from "react";
import { Plus, RefreshCw, Eye, Trash2, Edit } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader } from "@/components/ui/card";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
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
import { getDepartments } from "../services/api.js";
import DepartmentForm from "../components/forms/DepartmentForm.tsx";

export default function Departments() {
  const [departments, setDepartments] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [showCreateForm, setShowCreateForm] = useState(false);
  const [selectedDepartment, setSelectedDepartment] = useState<any>(null);
  const [showDepartmentDetail, setShowDepartmentDetail] = useState(false);
  const [showEditForm, setShowEditForm] = useState(false);

  // Fetch departments on component mount
  useEffect(() => {
    const fetchDepartments = async () => {
      try {
        setLoading(true);
        const data = await getDepartments();
        setDepartments(data);
      } catch (error) {
        console.error('Failed to fetch departments:', error);
      } finally {
        setLoading(false);
      }
    };

    fetchDepartments();
  }, []);

  // Refresh data function
  const handleRefresh = async () => {
    try {
      setLoading(true);
      const data = await getDepartments();
      setDepartments(data);
    } catch (error) {
      console.error('Failed to refresh departments:', error);
    } finally {
      setLoading(false);
    }
  };

  // Format date for display
  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleDateString();
  };

  // Handle form submit (create department)
  const handleFormSubmit = async (departmentData: any) => {
    try {
      await handleRefresh(); // Refresh the list
      setShowCreateForm(false);
    } catch (error) {
      console.error('Failed to save department:', error);
    }
  };

  // Handle view department details
  const handleViewDepartment = (department: any) => {
    window.location.href = `/departments/${department.id}`;
  };

  // Handle edit department
  const handleEditDepartment = (department: any) => {
    setSelectedDepartment(department);
    setShowEditForm(true);
  };

  // Handle edit form submit
  const handleEditFormSubmit = async (departmentData: any) => {
    try {
      await handleRefresh(); // Refresh the list
      setShowEditForm(false);
      setSelectedDepartment(null);
    } catch (error) {
      console.error('Failed to update department:', error);
    }
  };

  // Handle delete department
  const handleDeleteDepartment = async (departmentId: number) => {
    try {
      const response = await fetch(`/api/departments/${departmentId}`, {
        method: 'DELETE',
        headers: {
          'Authorization': `Bearer ${localStorage.getItem('auth_token')}`
        }
      });

      if (response.ok) {
        await handleRefresh(); // Refresh the list
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

  return (
    <div className="h-full flex flex-col">
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-bold text-foreground">Departments</h1>
        <Button variant="outline" size="sm" className="flex items-center space-x-2" onClick={handleRefresh} disabled={loading}>
          <RefreshCw className={`h-4 w-4 ${loading ? 'animate-spin' : ''}`} />
          <span>Refresh</span>
        </Button>
      </div>

      {/* Create Department Button */}
      <div className="mb-6">
        <Dialog open={showCreateForm} onOpenChange={setShowCreateForm}>
          <DialogTrigger asChild>
            <Button className="flex items-center space-x-2" data-create-department>
              <Plus className="h-4 w-4" />
              <span>Create Department</span>
            </Button>
          </DialogTrigger>
          <DialogContent className="max-w-2xl">
            <DepartmentForm
              onSubmit={handleFormSubmit}
              onCancel={() => setShowCreateForm(false)}
            />
          </DialogContent>
        </Dialog>
      </div>

      {/* Departments Table with Fixed Headers */}
      <div className="flex-1 overflow-hidden">
        <Card className="h-full flex flex-col">
          {/* Fixed Header */}
          <div className="bg-muted/50 border-b border-border p-0 flex-shrink-0">
            <div className="grid grid-cols-5 gap-4 p-4 font-semibold text-sm">
              <div>Department Name</div>
              <div>Department Owner</div>
              <div>Department Team</div>
              <div>Department Created Date</div>
              <div>Actions</div>
            </div>
          </div>
          
          {/* Scrollable Content */}
          <div className="flex-1 overflow-y-auto hide-scrollbar">
            {loading ? (
              <div className="flex justify-center items-center py-12">
                <p className="text-muted-foreground">Loading departments...</p>
              </div>
            ) : departments.length === 0 ? (
              <div className="flex justify-center items-center py-12">
                <p className="text-muted-foreground">No departments available</p>
              </div>
            ) : (
              <div className="divide-y divide-border">
                {departments.map((dept, index) => (
                  <div key={dept.id || index} className="grid grid-cols-5 gap-4 p-4 hover:bg-muted/50 transition-colors">
                    <div className="font-medium">{dept.name}</div>
                    <div className="text-sm text-muted-foreground">
                      {dept.manager_name || 'No Manager Assigned'}
                    </div>
                    <div className="text-sm text-muted-foreground">
                      {dept.team_members && dept.team_members.length > 0 ? (
                        <div className="space-y-1">
                          {dept.team_members.slice(0, 2).map((member: any) => (
                            <div key={member.id} className="flex items-center space-x-2">
                              <span>{member.first_name} {member.last_name}</span>
                              <span className="text-xs bg-blue-100 text-blue-800 px-2 py-0.5 rounded capitalize">
                                {member.role}
                              </span>
                            </div>
                          ))}
                          {dept.team_members.length > 2 && (
                            <div className="text-xs text-muted-foreground">
                              +{dept.team_members.length - 2} more
                            </div>
                          )}
                        </div>
                      ) : (
                        'No Team Members'
                      )}
                    </div>
                    <div className="text-sm text-muted-foreground">{formatDate(dept.created_at || dept.createdDate)}</div>
                    <div className="flex items-center space-x-1">
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={() => handleViewDepartment(dept)}
                        className="p-1 h-7 w-7"
                        title="View Department"
                      >
                        <Eye className="h-3 w-3" />
                      </Button>
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={() => handleEditDepartment(dept)}
                        className="p-1 h-7 w-7 text-blue-600 hover:text-blue-700 hover:bg-blue-50"
                        title="Edit Department"
                      >
                        <Edit className="h-3 w-3" />
                      </Button>
                      <AlertDialog>
                        <AlertDialogTrigger asChild>
                          <Button
                            variant="outline"
                            size="sm"
                            className="p-1 h-7 w-7 text-red-600 hover:text-red-700 hover:bg-red-50"
                            title="Delete Department"
                          >
                            <Trash2 className="h-3 w-3" />
                          </Button>
                        </AlertDialogTrigger>
                        <AlertDialogContent>
                          <AlertDialogHeader>
                            <AlertDialogTitle>Delete Department</AlertDialogTitle>
                            <AlertDialogDescription>
                              Are you sure you want to delete the "{dept.name}" department? 
                              This action cannot be undone and will remove all associated data.
                            </AlertDialogDescription>
                          </AlertDialogHeader>
                          <AlertDialogFooter>
                            <AlertDialogCancel>Cancel</AlertDialogCancel>
                            <AlertDialogAction
                              onClick={() => handleDeleteDepartment(dept.id)}
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

      {/* Department Detail Dialog */}
      <Dialog open={showDepartmentDetail} onOpenChange={setShowDepartmentDetail}>
        <DialogContent className="max-w-4xl max-h-[80vh] overflow-y-auto">
          {selectedDepartment && (
            <div className="space-y-6">
              <div className="flex items-center justify-between">
                <h2 className="text-2xl font-bold">{selectedDepartment.name}</h2>
                <div className="text-sm text-muted-foreground">
                  Created: {formatDate(selectedDepartment.created_at || selectedDepartment.createdDate)}
                </div>
              </div>

              {/* Department Manager */}
              <div className="space-y-2">
                <h3 className="text-lg font-semibold">Department Manager</h3>
                <div className="p-4 bg-muted/50 rounded-lg">
                  {selectedDepartment.manager_name ? (
                    <div className="flex items-center space-x-3">
                      <div className="w-10 h-10 bg-blue-500 rounded-full flex items-center justify-center text-white font-semibold">
                        {selectedDepartment.manager_name.charAt(0).toUpperCase()}
                      </div>
                      <div>
                        <div className="font-medium">{selectedDepartment.manager_name}</div>
                        <div className="text-sm text-muted-foreground">Manager</div>
                      </div>
                    </div>
                  ) : (
                    <div className="text-muted-foreground">No manager assigned</div>
                  )}
                </div>
              </div>

              {/* Team Members */}
              <div className="space-y-2">
                <h3 className="text-lg font-semibold">Team Members</h3>
                <div className="space-y-2">
                  {selectedDepartment.team_members && selectedDepartment.team_members.length > 0 ? (
                    selectedDepartment.team_members.map((member: any) => (
                      <div key={member.id} className="p-3 bg-muted/30 rounded-lg flex items-center justify-between">
                        <div className="flex items-center space-x-3">
                          <div className="w-8 h-8 bg-green-500 rounded-full flex items-center justify-center text-white text-sm font-semibold">
                            {member.first_name?.charAt(0).toUpperCase()}{member.last_name?.charAt(0).toUpperCase()}
                          </div>
                          <div>
                            <div className="font-medium">{member.first_name} {member.last_name}</div>
                            <div className="text-sm text-muted-foreground">{member.email}</div>
                          </div>
                        </div>
                        <div className="flex items-center space-x-2">
                          <span className="text-xs bg-blue-100 text-blue-800 px-2 py-1 rounded capitalize">
                            {member.role}
                          </span>
                          <span className={`text-xs px-2 py-1 rounded ${
                            member.is_active 
                              ? 'bg-green-100 text-green-800' 
                              : 'bg-red-100 text-red-800'
                          }`}>
                            {member.is_active ? 'Active' : 'Inactive'}
                          </span>
                        </div>
                      </div>
                    ))
                  ) : (
                    <div className="p-4 bg-muted/50 rounded-lg text-muted-foreground text-center">
                      No team members assigned to this department
                    </div>
                  )}
                </div>
              </div>

              {/* Department Statistics */}
              <div className="grid grid-cols-3 gap-4">
                <div className="p-4 bg-blue-50 rounded-lg text-center">
                  <div className="text-2xl font-bold text-blue-600">
                    {selectedDepartment.team_members ? selectedDepartment.team_members.length : 0}
                  </div>
                  <div className="text-sm text-blue-600">Total Members</div>
                </div>
                <div className="p-4 bg-green-50 rounded-lg text-center">
                  <div className="text-2xl font-bold text-green-600">
                    {selectedDepartment.team_members ? 
                      selectedDepartment.team_members.filter((m: any) => m.is_active).length : 0}
                  </div>
                  <div className="text-sm text-green-600">Active Members</div>
                </div>
                <div className="p-4 bg-amber-50 rounded-lg text-center">
                  <div className="text-2xl font-bold text-amber-600">
                    {selectedDepartment.manager_name ? 1 : 0}
                  </div>
                  <div className="text-sm text-amber-600">Manager Assigned</div>
                </div>
              </div>
            </div>
          )}
        </DialogContent>
      </Dialog>

      {/* Department Edit Dialog */}
      <Dialog open={showEditForm} onOpenChange={setShowEditForm}>
        <DialogContent className="max-w-2xl">
          <DepartmentForm
            department={selectedDepartment}
            onSubmit={handleEditFormSubmit}
            onCancel={() => {
              setShowEditForm(false);
              setSelectedDepartment(null);
            }}
          />
        </DialogContent>
      </Dialog>
    </div>
  );
}
