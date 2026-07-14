import * as React from "react";
import * as DropdownMenu from "@radix-ui/react-dropdown-menu";
import { Check, ChevronDown } from "lucide-react";
import { cn } from "@/lib/utils";

/**
 * A drop-in replacement for the Radix Select that renders its options in a
 * natively-scrollable list (with a visible, styled scrollbar) instead of the
 * hover scroll-buttons the Radix Select uses. Styling mirrors ui/select.tsx.
 */

interface ScrollSelectContextValue {
  value?: string;
  onValueChange: (value: string) => void;
}

const ScrollSelectContext = React.createContext<ScrollSelectContextValue>({
  onValueChange: () => {},
});

function ScrollSelect({
  value,
  onValueChange,
  children,
}: {
  value?: string;
  onValueChange: (value: string) => void;
  children: React.ReactNode;
}) {
  return (
    <ScrollSelectContext.Provider value={{ value, onValueChange }}>
      <DropdownMenu.Root>{children}</DropdownMenu.Root>
    </ScrollSelectContext.Provider>
  );
}

const ScrollSelectTrigger = React.forwardRef<
  React.ElementRef<typeof DropdownMenu.Trigger>,
  React.ComponentPropsWithoutRef<typeof DropdownMenu.Trigger>
>(({ className, children, ...props }, ref) => (
  <DropdownMenu.Trigger
    ref={ref}
    className={cn(
      "flex w-full items-center justify-between rounded-md border border-input bg-transparent px-3 py-2 text-sm shadow-sm focus:outline-none focus:ring-2 focus:ring-ring disabled:cursor-not-allowed disabled:opacity-50 [&>span]:line-clamp-1",
      className
    )}
    {...props}
  >
    {children}
    <ChevronDown className="h-4 w-4 shrink-0 opacity-50" />
  </DropdownMenu.Trigger>
));
ScrollSelectTrigger.displayName = "ScrollSelectTrigger";

const ScrollSelectContent = React.forwardRef<
  React.ElementRef<typeof DropdownMenu.Content>,
  React.ComponentPropsWithoutRef<typeof DropdownMenu.Content>
>(({ className, children, align = "start", sideOffset = 4, ...props }, ref) => (
  <DropdownMenu.Portal>
    <DropdownMenu.Content
      ref={ref}
      align={align}
      sideOffset={sideOffset}
      className={cn(
        "scrollbar-thin z-50 max-h-80 w-[var(--radix-dropdown-menu-trigger-width)] min-w-[8rem] overflow-y-auto overflow-x-hidden rounded-md border bg-popover p-1 text-popover-foreground shadow-md",
        className
      )}
      {...props}
    >
      {children}
    </DropdownMenu.Content>
  </DropdownMenu.Portal>
));
ScrollSelectContent.displayName = "ScrollSelectContent";

const ScrollSelectItem = React.forwardRef<
  React.ElementRef<typeof DropdownMenu.Item>,
  React.ComponentPropsWithoutRef<typeof DropdownMenu.Item> & { value: string }
>(({ className, children, value, ...props }, ref) => {
  const ctx = React.useContext(ScrollSelectContext);
  const selected = ctx.value === value;
  return (
    <DropdownMenu.Item
      ref={ref}
      onSelect={(e) => {
        e.preventDefault();
        ctx.onValueChange(value);
      }}
      className={cn(
        "relative flex w-full cursor-pointer select-none items-start rounded-sm py-1.5 pl-8 pr-2 text-sm outline-none focus:bg-accent focus:text-accent-foreground data-[disabled]:pointer-events-none data-[disabled]:opacity-50",
        className
      )}
      {...props}
    >
      {selected && (
        <span className="absolute left-2 top-2 flex h-3.5 w-3.5 items-center justify-center">
          <Check className="h-4 w-4" />
        </span>
      )}
      {children}
    </DropdownMenu.Item>
  );
});
ScrollSelectItem.displayName = "ScrollSelectItem";

export {
  ScrollSelect,
  ScrollSelectTrigger,
  ScrollSelectContent,
  ScrollSelectItem,
};
