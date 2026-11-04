import { useSyncExternalStore } from "react";
import { getAnnouncementsPref, subscribeAppearancePrefs } from "./appearancePrefs";

export const useAnnouncementsPref = () => useSyncExternalStore(subscribeAppearancePrefs, getAnnouncementsPref, getAnnouncementsPref);
