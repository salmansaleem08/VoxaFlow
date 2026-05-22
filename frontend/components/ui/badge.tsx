import * as React from "react"
import { cva, type VariantProps } from "class-variance-authority"
import { cn } from "@/lib/utils"

const badgeVariants = cva(
  "inline-flex items-center gap-1.5 rounded-full px-2.5 py-0.5 text-xs font-medium transition-colors",
  {
    variants: {
      variant: {
        default:  "bg-primary/10 text-primary border border-primary/20",
        secondary:"bg-secondary/10 text-secondary border border-secondary/20",
        success:  "bg-emerald-50 text-emerald-700 border border-emerald-200 dark:bg-emerald-950 dark:text-emerald-300",
        warning:  "bg-amber-50 text-amber-700 border border-amber-200 dark:bg-amber-950 dark:text-amber-300",
        destructive: "bg-destructive/10 text-destructive border border-destructive/20",
        outline:  "border border-border text-foreground",
        muted:    "bg-muted text-muted-foreground",
      },
    },
    defaultVariants: { variant: "default" },
  }
)

export interface BadgeProps
  extends React.HTMLAttributes<HTMLSpanElement>,
    VariantProps<typeof badgeVariants> {}

function Badge({ className, variant, ...props }: BadgeProps) {
  return <span className={cn(badgeVariants({ variant }), className)} {...props} />
}

export { Badge, badgeVariants }
