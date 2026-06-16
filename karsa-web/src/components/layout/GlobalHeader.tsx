'use client';

import React, { useState } from 'react';
import { useUIStore } from '../../state/useUIStore';
import { SearchCommandPalette } from '../shared/SearchCommandPalette';
import { useSearch } from '../../hooks/search';
import { usePathname } from 'next/navigation';
import { NAV_ITEMS } from '../../config/navigation';
import { useTheme } from 'next-themes';

import { useDebounce } from '../../hooks/useDebounce';

export function GlobalHeader() {
  const { isSearchOpen, setSearchOpen } = useUIStore();
  const [searchText, setSearchText] = useState("");
  const debouncedSearch = useDebounce(searchText, 300);
  const { theme, setTheme } = useTheme();
  
  // Wave-6 Integration
  const { data: searchResults, isLoading: isSearchLoading, isError: isSearchError } = useSearch(debouncedSearch);
  
  const pathname = usePathname();
  const currentNav = NAV_ITEMS.find(item => item.href === pathname);
  const pageTitle = currentNav ? currentNav.label : 'Karsa Web Console';

  return (
    <header className="flex h-16 items-center justify-between px-6 border-b bg-white dark:bg-slate-950">
      <h1 className="text-xl font-semibold">{pageTitle}</h1>
      <div className="flex items-center space-x-4">
        <button 
          onClick={() => setSearchOpen(true)}
          className="px-3 py-1.5 text-sm text-slate-500 bg-slate-100 dark:bg-slate-800 rounded-md flex items-center space-x-2"
        >
          <span>Search...</span>
          <kbd className="font-mono text-xs bg-slate-200 dark:bg-slate-700 px-1 rounded">Cmd K</kbd>
        </button>
        <button onClick={() => setTheme(theme === 'dark' ? 'light' : 'dark')} className="p-2 rounded-full hover:bg-slate-100">
          {theme === 'dark' ? '🌞' : '🌙'}
        </button>
      </div>

      <SearchCommandPalette 
        isOpen={isSearchOpen} 
        setIsOpen={setSearchOpen}
        searchText={searchText}
        setSearchText={setSearchText}
        results={searchResults?.results ?? []}
        isLoading={isSearchLoading}
        isError={isSearchError}
      />
    </header>
  );
}
