import React, { useEffect } from "react";
import {
  CommandDialog,
  CommandInput,
  CommandList,
  CommandEmpty,
  CommandGroup,
  CommandItem,
} from "../ui/command";

export interface SearchCommandPaletteProps {
  isOpen: boolean;
  setIsOpen: (isOpen: boolean) => void;
  searchText: string;
  setSearchText: (text: string) => void;
  results?: Array<{ id: string; label: string; subtitle?: string; type: string; route: string }>;
  isLoading?: boolean;
  isError?: boolean;
}

export function SearchCommandPalette({
  isOpen,
  setIsOpen,
  searchText,
  setSearchText,
  results = [],
  isLoading = false,
  isError = false,
}: SearchCommandPaletteProps) {
  useEffect(() => {
    const down = (e: KeyboardEvent) => {
      if (e.key === "k" && (e.metaKey || e.ctrlKey)) {
        e.preventDefault();
        setIsOpen(!isOpen);
      }
    };
    document.addEventListener("keydown", down);
    return () => document.removeEventListener("keydown", down);
  }, [isOpen, setIsOpen]);

  return (
    <CommandDialog open={isOpen} onOpenChange={setIsOpen}>
      <CommandInput
        placeholder="Type a command or search..."
        value={searchText}
        onValueChange={setSearchText}
      />
      <CommandList>
        {isLoading && <CommandEmpty>Searching...</CommandEmpty>}
        {isError && <CommandEmpty>Failed to fetch results.</CommandEmpty>}
        {!isLoading && !isError && searchText.length > 0 && results.length === 0 && (
          <CommandEmpty>No results found.</CommandEmpty>
        )}
        {!isLoading && !isError && results.length > 0 && (
          <CommandGroup heading="Results">
            {results.map((result) => (
              <CommandItem key={result.id} value={result.label} onSelect={() => {
                window.location.href = result.route;
                setIsOpen(false);
              }}>
                <div className="flex flex-col">
                  <span className="font-medium">{result.label}</span>
                  {result.subtitle && <span className="text-xs text-slate-500">{result.subtitle}</span>}
                </div>
                <span className="ml-auto text-xs bg-slate-100 dark:bg-slate-800 px-2 py-1 rounded">{result.type}</span>
              </CommandItem>
            ))}
          </CommandGroup>
        )}
      </CommandList>
    </CommandDialog>
  );
}
