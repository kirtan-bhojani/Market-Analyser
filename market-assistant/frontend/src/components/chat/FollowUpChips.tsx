interface FollowUpChipsProps {
  suggestions: string[];
  onPick: (suggestion: string) => void;
  disabled?: boolean;
}

export function FollowUpChips({ suggestions, onPick, disabled }: FollowUpChipsProps) {
  if (suggestions.length === 0) return null;
  return (
    <div className="follow-up-chips" aria-label="Suggested questions">
      {suggestions.map((s) => (
        <button
          key={s}
          type="button"
          className="follow-up-chip"
          disabled={disabled}
          onClick={() => onPick(s)}
        >
          {s}
        </button>
      ))}
    </div>
  );
}
