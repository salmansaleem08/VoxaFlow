import * as React from "react"
import { cn } from "@/lib/utils"

export interface InputProps extends React.InputHTMLAttributes<HTMLInputElement> {}

const Input = React.forwardRef<HTMLInputElement, InputProps>(
  ({ className, type, ...props }, ref) => (
    <input
      type={type}
      className={cn(
        "flex w-full min-w-0 rounded-md border border-input bg-transparent px-3 py-1 text-base",
        "placeholder:text-muted-foreground",
        "transition-colors",
        "focus-visible:outline-none focus-visible:border-ring focus-visible:ring-[3px] focus-visible:ring-ring/50",
        "disabled:cursor-not-allowed disabled:opacity-50 disabled:pointer-events-none",
        "aria-invalid:border-destructive aria-invalid:ring-destructive/20",
        "dark:bg-input/30",
        "h-9",
        className
      )}
      ref={ref}
      {...props}
    />
  )
)
Input.displayName = "Input"

export { Input }
