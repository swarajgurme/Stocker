import type { ReactNode } from "react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { cn } from "@/lib/utils";

export function ChartCard({
  title,
  description,
  badge,
  children,
  className,
  height = "h-72",
}: {
  title: string;
  description?: string;
  badge?: string;
  children: ReactNode;
  className?: string;
  height?: string;
}) {
  return (
    <Card className={cn(className)} glow>
      <CardHeader className="flex flex-row flex-wrap items-center justify-between gap-2">
        <div>
          <CardTitle>{title}</CardTitle>
          {description ? <CardDescription>{description}</CardDescription> : null}
        </div>
        {badge ? <Badge tone="muted">{badge}</Badge> : null}
      </CardHeader>
      <CardContent className={cn(height, "min-h-[200px]")}>{children}</CardContent>
    </Card>
  );
}
