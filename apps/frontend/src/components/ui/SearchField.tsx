import { FormEvent } from "react";
import { Search } from "lucide-react";

import { cn } from "@/lib/utils";

interface SearchFieldProps {
  id: string;
  label: string;
  value: string;
  placeholder?: string;
  className?: string;
  onChange: (value: string) => void;
  onSubmit?: (value: string) => void;
}

export function SearchField({
  id,
  label,
  value,
  placeholder,
  className,
  onChange,
  onSubmit,
}: SearchFieldProps) {
  const handleSubmit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    onSubmit?.(value);
  };

  return (
    <form
      role="search"
      className={cn("relative", className)}
      aria-label={label}
      onSubmit={handleSubmit}
      noValidate
    >
      <label htmlFor={id} className="sr-only">
        {label}
      </label>
      <input
        id={id}
        name={id}
        type="search"
        value={value}
        placeholder={placeholder}
        onChange={(event) => onChange(event.target.value)}
        autoComplete="off"
        autoCorrect="off"
        enterKeyHint="search"
        className="w-full rounded-[var(--radius-md)] border border-[var(--primary-100)] bg-white/85 px-4 py-2 pr-11 text-sm text-[var(--text-primary)] shadow-sm transition-colors focus-visible:ring-2 focus-visible:ring-[var(--info-200)] focus-visible:ring-offset-1"
      />
      <span className="pointer-events-none absolute inset-y-0 right-3 flex items-center text-[var(--text-tertiary)]">
        <Search className="h-4 w-4" />
      </span>
    </form>
  );
}
