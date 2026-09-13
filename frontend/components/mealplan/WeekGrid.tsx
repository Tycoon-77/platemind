import type { FC } from "react";
import MealSlot, { type MealSlotProps } from "./MealSlot";

const DAYS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"];
const SLOTS = ["breakfast", "lunch", "dinner"] as const;

export type SlotKey = `${number}-${"breakfast" | "lunch" | "dinner"}`;
export type MealPlanData = Record<SlotKey, MealSlotProps["recipe"] | undefined>;

export interface WeekGridProps {
  mealPlan?: MealPlanData;
  onSlotSwap?: (day: number, slot: string) => void;
}

const WeekGrid: FC<WeekGridProps> = ({ mealPlan = {}, onSlotSwap }) => {
  return (
    <div className="overflow-x-auto pb-4">
      <table className="w-full border-separate border-spacing-y-3 border-spacing-x-2 min-w-[1000px]">
        <thead>
          <tr>
            <th className="w-20" />
            {DAYS.map((day) => (
              <th key={day} className="text-sm font-semibold text-muted-foreground pb-2 text-center uppercase tracking-wider">
                {day}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {SLOTS.map((slot) => (
            <tr key={slot}>
              <td className="text-xs font-bold text-muted-foreground uppercase tracking-wider pr-4 text-right">
                {slot}
              </td>
              {DAYS.map((_, dayIndex) => {
                const key: SlotKey = `${dayIndex}-${slot}`;
                return (
                  <td key={dayIndex} className="w-[14%] align-top">
                    <MealSlot
                      recipe={mealPlan[key]}
                      onSwapClick={onSlotSwap ? () => onSlotSwap(dayIndex, slot) : undefined}
                    />
                  </td>
                );
              })}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
};

export default WeekGrid;
