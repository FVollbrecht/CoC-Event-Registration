import { Card, CardContent } from "@/components/ui/card";
import { formatDistanceToNow } from "date-fns";

interface EventStatusCardProps {
  stats?: {
    totalRegistrations: number;
    currentCount: number;
    availableSpots: number;
    maxCapacity: number;
  };
  activityLogs: any[];
}

export default function EventStatusCard({ stats, activityLogs }: EventStatusCardProps) {
  if (!stats) {
    return (
      <div className="md:col-span-1">
        <Card className="bg-[#36393f] border-gray-700 shadow-lg overflow-hidden">
          <CardContent className="p-6">
            <h2 className="text-xl font-semibold mb-4">Event Status</h2>
            <div className="animate-pulse space-y-4">
              <div className="h-4 bg-gray-700 rounded w-3/4"></div>
              <div className="h-8 bg-gray-700 rounded"></div>
              <div className="grid grid-cols-2 gap-4 mt-4">
                <div className="h-20 bg-gray-700 rounded"></div>
                <div className="h-20 bg-gray-700 rounded"></div>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>
    );
  }

  const percentFilled = Math.floor((stats.currentCount / stats.maxCapacity) * 100);

  return (
    <div className="md:col-span-1">
      <Card className="bg-[#36393f] border-gray-700 shadow-lg overflow-hidden">
        <CardContent className="p-6">
          <h2 className="text-xl font-semibold mb-4">Event Status</h2>
          
          <div className="space-y-4">
            {/* Capacity Display */}
            <div>
              <div className="flex justify-between mb-2">
                <span className="text-gray-400">Registration Capacity</span>
                <span className="font-medium">
                  <span className="text-[#57F287] font-bold">{stats.currentCount}</span>
                  <span>/</span>
                  <span>{stats.maxCapacity}</span>
                </span>
              </div>
              <div className="w-full bg-gray-700 rounded-full h-2.5">
                <div 
                  className="bg-[#57F287] h-2.5 rounded-full" 
                  style={{ width: `${percentFilled}%` }}
                ></div>
              </div>
            </div>
            
            <div className="grid grid-cols-2 gap-4 mt-4">
              {/* Available Spots */}
              <div className="bg-[#36393f] border border-gray-700 rounded-lg p-4">
                <p className="text-sm text-gray-400">Available Spots</p>
                <p className="text-2xl font-bold text-[#57F287]">{stats.availableSpots}</p>
              </div>
              
              {/* Registrations */}
              <div className="bg-[#36393f] border border-gray-700 rounded-lg p-4">
                <p className="text-sm text-gray-400">Registrations</p>
                <p className="text-2xl font-bold text-[#5865F2]">{stats.totalRegistrations}</p>
              </div>
            </div>
            
            {/* Security Limits Info */}
            <div className="mt-4 bg-[#2f3136] border border-yellow-600 rounded-lg p-4">
              <h3 className="font-medium mb-2 flex items-center text-yellow-400">
                <svg xmlns="http://www.w3.org/2000/svg" className="h-4 w-4 mr-1" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                </svg>
                Registrierungslimits
              </h3>
              <ul className="text-sm space-y-1 text-gray-300">
                <li>• Maximal <span className="font-bold text-yellow-400">18 Teilnehmer</span> pro Benutzer</li>
                <li>• Maximal <span className="font-bold text-yellow-400">18 Teilnehmer</span> pro einzelnem Team</li>
                <li>• Gesamtkapazität: <span className="font-bold text-yellow-400">{stats.maxCapacity} Teilnehmer</span></li>
              </ul>
            </div>
            
            <div className="pt-4 border-t border-gray-700">
              <h3 className="font-medium mb-3">Recent Activity</h3>
              <div className="space-y-2 text-sm">
                {activityLogs.length > 0 ? (
                  activityLogs.map((log) => (
                    <div key={log.id} className="flex items-start py-2 border-b border-gray-700">
                      <div className={`w-2 h-2 rounded-full mt-1.5 mr-2 
                        ${log.type === 'register' ? 'bg-[#57F287]' : 
                          log.type === 'update' ? 'bg-[#FEE75C]' : 
                          'bg-[#ED4245]'}`}
                      ></div>
                      <div>
                        <span className="font-medium text-[#5865F2]">{log.name}</span>
                        {log.type === 'register' && (
                          <> registered <span className="font-medium">{log.newCount}</span> participants</>
                        )}
                        {log.type === 'update' && (
                          <> updated from <span className="font-medium">{log.oldCount}</span> to <span className="font-medium">{log.newCount}</span> participants</>
                        )}
                        {log.type === 'cancel' && (
                          <> canceled their registration</>
                        )}
                        <div className="text-xs text-gray-400">
                          {formatDistanceToNow(new Date(log.timestamp), { addSuffix: true })}
                        </div>
                      </div>
                    </div>
                  ))
                ) : (
                  <div className="text-gray-400 py-2">No recent activity</div>
                )}
              </div>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
