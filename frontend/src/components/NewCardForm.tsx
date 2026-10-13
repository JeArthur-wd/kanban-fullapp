import { useState, type FormEvent } from "react";
import { PlusIcon } from "@/components/icons";

const initialFormState = { title: "", details: "" };

const fieldClass =
  "w-full rounded-md border border-line bg-surface px-2.5 py-1.5 text-sm text-ink transition-colors hover:border-line-strong focus:border-accent";

type NewCardFormProps = {
  onAdd: (title: string, details: string) => void;
};

export const NewCardForm = ({ onAdd }: NewCardFormProps) => {
  const [isOpen, setIsOpen] = useState(false);
  const [formState, setFormState] = useState(initialFormState);

  const handleSubmit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (!formState.title.trim()) {
      return;
    }
    onAdd(formState.title.trim(), formState.details.trim());
    setFormState(initialFormState);
    setIsOpen(false);
  };

  return (
    <div className="mt-2">
      {isOpen ? (
        <form
          onSubmit={handleSubmit}
          className="space-y-2 rounded-lg border border-line bg-surface p-2.5 shadow-card"
        >
          <input
            value={formState.title}
            onChange={(event) =>
              setFormState((prev) => ({ ...prev, title: event.target.value }))
            }
            placeholder="Card title"
            aria-label="Card title"
            className={`${fieldClass} font-medium`}
            autoFocus
            required
          />
          <textarea
            value={formState.details}
            onChange={(event) =>
              setFormState((prev) => ({ ...prev, details: event.target.value }))
            }
            placeholder="Details"
            aria-label="Card details"
            rows={3}
            className={`${fieldClass} resize-none`}
          />
          <div className="flex items-center gap-2">
            <button
              type="submit"
              className="h-8 rounded-md bg-accent px-3 text-[13px] font-medium text-white transition-colors hover:bg-accent-strong"
            >
              Add card
            </button>
            <button
              type="button"
              onClick={() => {
                setIsOpen(false);
                setFormState(initialFormState);
              }}
              className="h-8 rounded-md px-3 text-[13px] font-medium text-muted transition-colors hover:bg-well hover:text-ink"
            >
              Cancel
            </button>
          </div>
        </form>
      ) : (
        <button
          type="button"
          onClick={() => setIsOpen(true)}
          className="flex h-8 w-full items-center gap-1.5 rounded-md px-2 text-[13px] font-medium text-muted transition-colors hover:bg-surface/80 hover:text-ink"
        >
          <PlusIcon width={14} height={14} />
          Add a card
        </button>
      )}
    </div>
  );
};
