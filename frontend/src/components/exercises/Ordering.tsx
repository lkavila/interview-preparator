import {
  DndContext,
  KeyboardSensor,
  PointerSensor,
  closestCenter,
  useSensor,
  useSensors,
  type DragEndEvent,
} from "@dnd-kit/core";
import {
  SortableContext,
  arrayMove,
  sortableKeyboardCoordinates,
  useSortable,
  verticalListSortingStrategy,
} from "@dnd-kit/sortable";
import { CSS } from "@dnd-kit/utilities";
import { useTranslation } from "react-i18next";
import { pick } from "../../lib/lang";
import type { Bilingual } from "../../lib/types";

interface Item {
  id: string;
  label: Bilingual;
}

interface Props {
  items: Item[];
  order: string[]; // current arrangement (ids)
  onChange: (order: string[]) => void;
  disabled?: boolean;
  layout?: "flow" | "list";
}

function SortableBox({
  id,
  label,
  index,
  disabled,
  isFlow,
}: {
  id: string;
  label: string;
  index: number;
  disabled?: boolean;
  isFlow: boolean;
}) {
  const { attributes, listeners, setNodeRef, transform, transition, isDragging } = useSortable({
    id,
    disabled,
  });
  return (
    <div className="flex flex-col items-stretch">
      <div
        ref={setNodeRef}
        style={{ transform: CSS.Transform.toString(transform), transition }}
        {...attributes}
        {...listeners}
        className={`flex items-center gap-3 rounded-lg border border-border bg-surface px-3.5 py-2.5 text-[13.5px] ${
          disabled ? "" : "cursor-grab active:cursor-grabbing"
        } ${isDragging ? "z-10 border-accent shadow-lg" : ""}`}
      >
        <span className="flex h-5 w-5 shrink-0 items-center justify-center rounded bg-surface2 font-mono text-[11px] text-muted">
          {index + 1}
        </span>
        <span>{label}</span>
        {!disabled && (
          <svg
            width="13"
            height="13"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="2"
            className="ml-auto shrink-0 text-muted"
          >
            <line x1="4" y1="9" x2="20" y2="9" />
            <line x1="4" y1="15" x2="20" y2="15" />
          </svg>
        )}
      </div>
      {isFlow && (
        <div className="flex justify-center py-0.5 text-muted last:hidden" aria-hidden>
          <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <line x1="12" y1="4" x2="12" y2="20" />
            <polyline points="6 14 12 20 18 14" />
          </svg>
        </div>
      )}
    </div>
  );
}

/** Drag-the-boxes exercise. With layout "flow" it renders as an architecture
 * flow (boxes connected by arrows) to build e.g. Client -> Gateway -> Service -> DB. */
export default function Ordering({ items, order, onChange, disabled, layout }: Props) {
  const { t, i18n } = useTranslation();
  const sensors = useSensors(
    useSensor(PointerSensor, { activationConstraint: { distance: 4 } }),
    useSensor(KeyboardSensor, { coordinateGetter: sortableKeyboardCoordinates })
  );

  const byId = new Map(items.map((i) => [i.id, i]));
  const isFlow = layout === "flow";

  const handleDragEnd = (event: DragEndEvent) => {
    const { active, over } = event;
    if (over && active.id !== over.id) {
      const oldIndex = order.indexOf(String(active.id));
      const newIndex = order.indexOf(String(over.id));
      onChange(arrayMove(order, oldIndex, newIndex));
    }
  };

  return (
    <div>
      <p className="mb-2 text-[12.5px] text-muted">{t("orderInstruction")}</p>
      <DndContext sensors={sensors} collisionDetection={closestCenter} onDragEnd={handleDragEnd}>
        <SortableContext items={order} strategy={verticalListSortingStrategy}>
          <div className={isFlow ? "flex flex-col" : "flex flex-col gap-2"}>
            {order.map((id, idx) => {
              const item = byId.get(id);
              if (!item) return null;
              return (
                <SortableBox
                  key={id}
                  id={id}
                  index={idx}
                  label={pick(item.label, i18n.language)}
                  disabled={disabled}
                  isFlow={isFlow && idx < order.length - 1}
                />
              );
            })}
          </div>
        </SortableContext>
      </DndContext>
    </div>
  );
}
