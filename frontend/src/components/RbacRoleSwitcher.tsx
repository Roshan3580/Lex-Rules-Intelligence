import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Badge } from "@/components/ui/badge";
import { Shield } from "lucide-react";
import { AppRoleId, setAppRole, getAppRole } from "@/lib/api";
import { useEffect, useState } from "react";

const ORDER: AppRoleId[] = ["viewer", "reviewer", "admin"];

export function RbacRoleSwitcher() {
  const [role, setRole] = useState<AppRoleId>(() => getAppRole());

  useEffect(() => {
    const sync = () => setRole(getAppRole());
    window.addEventListener("rules_intel_app_role", sync);
    window.addEventListener("storage", sync);
    return () => {
      window.removeEventListener("rules_intel_app_role", sync);
      window.removeEventListener("storage", sync);
    };
  }, []);

  return (
    <div className="flex items-center gap-2 shrink-0">
      <Shield className="h-3.5 w-3.5 text-muted-foreground" aria-hidden />
      <Select
        value={role}
        onValueChange={(v) => {
          const next = v as AppRoleId;
          setAppRole(next);
          setRole(next);
        }}
      >
        <SelectTrigger className="h-9 w-[128px] text-xs rounded-md bg-secondary/70 border-border/80">
          <SelectValue placeholder="Role" />
        </SelectTrigger>
        <SelectContent align="end">
          {ORDER.map((r) => (
            <SelectItem key={r} value={r} className="text-xs capitalize">
              {r}
            </SelectItem>
          ))}
        </SelectContent>
      </Select>
      <Badge
        variant="outline"
        className="hidden sm:inline-flex text-[10px] font-normal max-w-[200px]"
        title="Sent as X-User-Role on API calls (demo RBAC)."
      >
        API: <span className="ml-1 font-medium capitalize">{role}</span>
      </Badge>
    </div>
  );
}
