"use client";

import { useState, type KeyboardEvent } from "react";
import { SearchIcon, XIcon, PlusIcon } from "lucide-react";

export interface PantryInputProps {
  initialTags?: string[];
  onSearch?: (ingredients: string[]) => void;
}

const COMMON_STAPLES = ["garlic", "onion", "olive oil", "eggs", "butter"];

const PantryInput = ({ onSearch, initialTags = [] }: PantryInputProps) => {
  const [tags, setTags] = useState<string[]>(initialTags);
  const [inputValue, setInputValue] = useState("");
  
  const addTag = (value: string) => {
    const trimmed = value.trim().toLowerCase();
    if (trimmed && !tags.includes(trimmed)) {
      setTags((prev) => [...prev, trimmed]);
    }
    setInputValue("");
  };

  const removeTag = (tag: string) => {
    setTags((prev) => prev.filter((t) => t !== tag));
  };

  const handleKeyDown = (e: KeyboardEvent<HTMLInputElement>) => {
    if (e.key === "Enter" || e.key === ",") {
      e.preventDefault();
      addTag(inputValue);
    } else if (e.key === "Backspace" && !inputValue && tags.length > 0) {
      removeTag(tags[tags.length - 1]);
    }
  };

  return (
    <div className="space-y-4">
      <div className="flex flex-col space-y-3">
        <label className="text-sm font-semibold text-foreground">What&apos;s in your pantry?</label>
        
        {/* Main Input Box */}
        <div className="flex flex-wrap gap-2 p-3 border border-border rounded-xl bg-card min-h-[3.5rem] focus-within:ring-2 focus-within:ring-primary/20 transition-all shadow-sm">
          {tags.map((tag) => (
            <span
              key={tag}
              className="inline-flex items-center gap-1.5 rounded-md bg-secondary px-3 py-1 text-sm font-medium text-secondary-foreground"
            >
              {tag}
              <button
                onClick={() => removeTag(tag)}
                className="text-muted-foreground hover:text-foreground leading-none transition-colors"
                aria-label={`Remove ${tag}`}
              >
                <XIcon className="w-3.5 h-3.5" />
              </button>
            </span>
          ))}
          <input
            type="text"
            value={inputValue}
            onChange={(e) => setInputValue(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder={tags.length === 0 ? "Type ingredients (e.g. eggs, tomatoes...)" : ""}
            className="flex-1 min-w-[150px] outline-none text-sm text-foreground bg-transparent placeholder:text-muted-foreground"
          />
        </div>

        {/* Quick Add Staples */}
        <div className="flex flex-wrap gap-2 items-center text-sm">
          <span className="text-muted-foreground text-xs font-medium uppercase tracking-wider mr-1">Quick add:</span>
          {COMMON_STAPLES.filter(s => !tags.includes(s)).map((staple) => (
            <button
              key={staple}
              onClick={() => addTag(staple)}
              className="inline-flex items-center gap-1 text-xs px-2.5 py-1 rounded-full border border-border bg-background hover:bg-secondary text-muted-foreground hover:text-foreground transition-colors"
            >
              <PlusIcon className="w-3 h-3" />
              {staple}
            </button>
          ))}
        </div>
      </div>

      {/* Action button */}
      <button
        onClick={() => onSearch?.(tags)}
        disabled={tags.length === 0}
        className="w-full flex items-center justify-center gap-2 rounded-xl bg-primary hover:bg-primary/90 disabled:opacity-50 disabled:cursor-not-allowed text-primary-foreground font-semibold py-3.5 transition-all duration-200 shadow-sm"
      >
        <SearchIcon className="w-5 h-5" />
        Find Recipes
      </button>
    </div>
  );
};

export default PantryInput;
