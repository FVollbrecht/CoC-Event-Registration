import { useState } from "react";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Search, Download, Plus, Info } from "lucide-react";
import RegistrationsTable from "./RegistrationsTable";
import RegistrationForm from "./RegistrationForm";
import { Registration } from "@shared/schema";
import { useToast } from "@/hooks/use-toast";
import { apiRequest } from "@/lib/queryClient";
import { queryClient } from "@/lib/queryClient";
import { useAuth } from "@/hooks/use-auth";

interface RegistrationManagementCardProps {
  registrations: Registration[];
  onDeleteClick: (id: number) => void;
}

export default function RegistrationManagementCard({ 
  registrations, 
  onDeleteClick 
}: RegistrationManagementCardProps) {
  const [showForm, setShowForm] = useState(false);
  const [searchTerm, setSearchTerm] = useState("");
  const { toast } = useToast();
  const { user, isAdmin } = useAuth();
  
  // Filtere Registrierungen nach Suchbegriff und Benutzerrechten
  const filteredRegistrations = registrations
    .filter(reg => reg.name.toLowerCase().includes(searchTerm.toLowerCase()))
    // Wenn kein Admin, dann nur eigene Registrierungen anzeigen
    .filter(reg => isAdmin || (user && reg.discordUserId === user.discordUserId));

  const handleExport = () => {
    try {
      // Create CSV content
      const headers = "ID,Team/Group,Participants,Registered By,Date\n";
      const rows = registrations.map(reg => 
        `${reg.id},"${reg.name}",${reg.count},"${reg.discordUsername}","${reg.registeredAt ? new Date(reg.registeredAt).toLocaleString() : 'N/A'}"`
      ).join("\n");
      
      const csvContent = headers + rows;
      
      // Create a Blob and download link
      const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
      const url = URL.createObjectURL(blob);
      const link = document.createElement("a");
      
      link.setAttribute("href", url);
      link.setAttribute("download", "registrations.csv");
      link.style.visibility = 'hidden';
      
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      
      toast({
        title: "Export successful",
        description: "Registrations have been exported to CSV",
      });
    } catch (error) {
      toast({
        title: "Export failed",
        description: "There was an error exporting the registrations",
        variant: "destructive",
      });
    }
  };

  const handleDelete = async (id: number) => {
    try {
      await apiRequest("DELETE", `/api/registrations/${id}`);
      
      // Update cache
      queryClient.invalidateQueries({ queryKey: ["/api/registrations"] });
      queryClient.invalidateQueries({ queryKey: ["/api/stats"] });
      queryClient.invalidateQueries({ queryKey: ["/api/activity"] });
      
      toast({
        title: "Registration deleted",
        description: "The registration has been successfully deleted",
      });
    } catch (error) {
      toast({
        title: "Delete failed",
        description: "There was an error deleting the registration",
        variant: "destructive",
      });
    }
  };

  return (
    <div className="md:col-span-2">
      <Card className="bg-[#36393f] border-gray-700 shadow-lg overflow-hidden">
        <CardContent className="p-6">
          <div className="flex justify-between items-center mb-6">
            <h2 className="text-xl font-semibold">
              {isAdmin ? "Alle Registrierungen" : "Deine Team-Registrierungen"}
            </h2>
            <div className="flex space-x-2">
              {isAdmin && (
                <Button 
                  variant="default" 
                  className="bg-[#5865F2] hover:bg-opacity-80"
                  onClick={handleExport}
                >
                  <Download className="mr-2 h-4 w-4" />
                  Export
                </Button>
              )}
              <Button 
                variant="default"
                className="bg-[#57F287] hover:bg-opacity-80"
                onClick={() => setShowForm(true)}
              >
                <Plus className="mr-2 h-4 w-4" />
                Team hinzufügen
              </Button>
            </div>
          </div>
          
          {/* Registration Form */}
          <RegistrationForm 
            isVisible={showForm} 
            onCancel={() => setShowForm(false)} 
            onSuccess={() => {
              setShowForm(false);
              queryClient.invalidateQueries({ queryKey: ["/api/registrations"] });
              queryClient.invalidateQueries({ queryKey: ["/api/stats"] });
              queryClient.invalidateQueries({ queryKey: ["/api/activity"] });
            }}
          />
          
          {/* Command Help */}
          <div className="bg-[#2f3136] border border-gray-700 rounded-md p-4 mb-6">
            <div className="flex items-start">
              <Info className="text-[#5865F2] flex-shrink-0 mt-0.5 mr-3" />
              <div>
                <h4 className="font-medium text-[#5865F2]">Discord Command</h4>
                <p className="text-sm text-gray-300 mt-1">Users can register using the command:</p>
                <div className="mt-2 bg-[#202225] px-3 py-2 rounded font-mono text-sm">
                  !reg #TeamName #NumberOfParticipants
                </div>
                <p className="text-xs text-gray-400 mt-2">
                  Example: <code>!reg #TeamAwesome #4</code> registers 4 participants for team "TeamAwesome"
                </p>
              </div>
            </div>
          </div>
          
          {/* Filters */}
          <div className="flex flex-wrap gap-4 mb-4">
            <div className="relative flex-grow">
              <Search className="absolute left-3 top-2.5 text-gray-400 h-4 w-4" />
              <Input
                placeholder="Search teams..."
                className="pl-9 bg-[#2f3136] border-gray-600 text-white"
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
              />
            </div>
          </div>
          
          {/* Registration Table */}
          <RegistrationsTable 
            registrations={filteredRegistrations} 
            onDeleteClick={onDeleteClick}
            onDelete={handleDelete}
          />
        </CardContent>
      </Card>
    </div>
  );
}
