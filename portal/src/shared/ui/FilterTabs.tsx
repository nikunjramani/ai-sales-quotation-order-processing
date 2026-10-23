export interface FilterTab {
  id: string;
  label: string;
}

interface Props {
  tabs: readonly FilterTab[];
  selected: string;
  onSelect: (id: string) => void;
}

export function FilterTabs({ tabs, selected, onSelect }: Props) {
  return (
    <div className="tabs" role="tablist">
      {tabs.map((tab) => (
        <button
          key={tab.id}
          role="tab"
          aria-selected={tab.id === selected}
          className={tab.id === selected ? "tab active" : "tab"}
          onClick={() => onSelect(tab.id)}
        >
          {tab.label}
        </button>
      ))}
    </div>
  );
}
