import { useQuery } from "@tanstack/react-query";
import EventStatusCard from "@/components/EventStatusCard";
import RegistrationManagementCard from "@/components/RegistrationManagementCard";
import { useState } from "react";
import ConfirmationModal from "@/components/ConfirmationModal";
import { EventConfig, Registration } from "@shared/schema";
import { useAuth } from "@/hooks/use-auth";
import { Link } from "wouter";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import { ChevronDown, LogOut, Settings, User, UserCog } from "lucide-react";

export default function Dashboard() {
  const [showDeleteModal, setShowDeleteModal] = useState(false);
  const [deleteId, setDeleteId] = useState<number | null>(null);
  const { user, isAdmin, logoutMutation } = useAuth();

  // Fetch config
  const { data: config } = useQuery<EventConfig>({
    queryKey: ["/api/config"],
  });

  // Fetch registrations
  const { data: registrations } = useQuery<Registration[]>({
    queryKey: ["/api/registrations"],
  });

  // Fetch stats
  const { data: stats } = useQuery<{
    totalRegistrations: number;
    currentCount: number;
    availableSpots: number;
    maxCapacity: number;
  }>({
    queryKey: ["/api/stats"],
  });

  // Fetch activity logs
  const { data: activityLogs } = useQuery<any[]>({
    queryKey: ["/api/activity"],
  });

  const handleDeleteClick = (id: number) => {
    setDeleteId(id);
    setShowDeleteModal(true);
  };

  return (
    <div className="flex flex-col min-h-screen bg-[#2f3136] text-white font-[Inter]">
      <header className="bg-[#202225] py-4 px-6 shadow-md">
        <div className="container mx-auto flex justify-between items-center">
          <div className="flex items-center space-x-3">
            <svg
              xmlns="http://www.w3.org/2000/svg"
              width="28"
              height="28"
              fill="currentColor"
              viewBox="0 0 16 16"
              className="text-[#5865F2]"
            >
              <path d="M13.545 2.907a13.227 13.227 0 0 0-3.257-1.011.05.05 0 0 0-.052.025c-.141.25-.297.577-.406.833a12.19 12.19 0 0 0-3.658 0 8.258 8.258 0 0 0-.412-.833.051.051 0 0 0-.052-.025c-1.125.194-2.22.534-3.257 1.011a.041.041 0 0 0-.021.018C.356 6.024-.213 9.047.066 12.032c.001.014.01.028.021.037a13.276 13.276 0 0 0 3.995 2.02.05.05 0 0 0 .056-.019c.308-.42.582-.863.818-1.329a.05.05 0 0 0-.01-.059.051.051 0 0 0-.018-.011 8.875 8.875 0 0 1-1.248-.595.05.05 0 0 1-.02-.066.051.051 0 0 1 .015-.019c.084-.063.168-.129.248-.195a.05.05 0 0 1 .051-.007c2.619 1.196 5.454 1.196 8.041 0a.052.052 0 0 1 .053.007c.08.066.164.132.248.195a.051.051 0 0 1-.004.085 8.254 8.254 0 0 1-1.249.594.05.05 0 0 0-.03.03.052.052 0 0 0 .003.041c.24.465.515.909.817 1.329a.05.05 0 0 0 .056.019 13.235 13.235 0 0 0 4.001-2.02.049.049 0 0 0 .021-.037c.334-3.451-.559-6.449-2.366-9.106a.034.034 0 0 0-.02-.019Zm-8.198 7.307c-.789 0-1.438-.724-1.438-1.612 0-.889.637-1.613 1.438-1.613.807 0 1.45.73 1.438 1.613 0 .888-.637 1.612-1.438 1.612Zm5.316 0c-.788 0-1.438-.724-1.438-1.612 0-.889.637-1.613 1.438-1.613.807 0 1.451.73 1.438 1.613 0 .888-.631 1.612-1.438 1.612Z" />
            </svg>
            <h1 className="text-2xl font-bold">CoC - bekackte Anmeldung</h1>
          </div>
          <div className="flex items-center gap-3">
            <div className="bg-[#40444b] px-3 py-1 rounded-full text-sm flex items-center mr-3">
              <span className="h-2 w-2 rounded-full bg-[#57F287] mr-2"></span>
              <span>{config?.serverName || "Discord Server"}</span>
            </div>
            
            {user && (
              <DropdownMenu>
                <DropdownMenuTrigger className="flex items-center gap-2 bg-[#36393f] px-2 py-1 rounded-md hover:bg-[#40444b] transition-colors">
                  <Avatar className="h-8 w-8 border border-[#5865F2]">
                    <AvatarFallback className="bg-[#5865F2] text-white">
                      {user.username.substring(0, 2).toUpperCase()}
                    </AvatarFallback>
                  </Avatar>
                  <span className="text-sm font-medium mr-1">{user.username}</span>
                  <ChevronDown className="h-4 w-4" />
                </DropdownMenuTrigger>
                <DropdownMenuContent align="end" className="w-56">
                  <DropdownMenuLabel className="flex items-center gap-2">
                    <User className="h-4 w-4" />
                    <span>Mein Konto</span>
                  </DropdownMenuLabel>
                  <DropdownMenuSeparator />
                  {isAdmin && (
                    <DropdownMenuItem asChild>
                      <Link to="/admin" className="flex items-center gap-2 cursor-pointer">
                        <UserCog className="h-4 w-4" />
                        <span>Administration</span>
                      </Link>
                    </DropdownMenuItem>
                  )}
                  <DropdownMenuItem asChild>
                    <Link to="/" className="flex items-center gap-2 cursor-pointer">
                      <Settings className="h-4 w-4" />
                      <span>Einstellungen</span>
                    </Link>
                  </DropdownMenuItem>
                  <DropdownMenuSeparator />
                  <DropdownMenuItem 
                    className="text-red-500 focus:text-red-500 cursor-pointer" 
                    onClick={() => logoutMutation.mutate()}
                  >
                    <LogOut className="h-4 w-4 mr-2" />
                    <span>Abmelden</span>
                  </DropdownMenuItem>
                </DropdownMenuContent>
              </DropdownMenu>
            )}
          </div>
        </div>
      </header>

      <main className="flex-grow container mx-auto py-6 px-4">
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          <EventStatusCard 
            stats={stats}
            activityLogs={activityLogs || []}
          />
          
          <RegistrationManagementCard 
            registrations={registrations || []}
            onDeleteClick={handleDeleteClick}
          />
        </div>
      </main>

      <footer className="bg-[#202225] py-4 px-6 text-center text-sm text-gray-400">
        <p>
          Event Registration Bot | <span className="text-[#5865F2]">Version 1.0.0</span>
        </p>
      </footer>

      <ConfirmationModal
        isOpen={showDeleteModal}
        onClose={() => setShowDeleteModal(false)}
        onConfirm={() => {
          // Handle delete confirmation
          setShowDeleteModal(false);
          // The actual delete logic is in the RegistrationManagementCard component
        }}
        deleteId={deleteId}
      />
    </div>
  );
}
