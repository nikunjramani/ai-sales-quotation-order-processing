import type { RouteObject } from "react-router";

import { ContactDetailPage } from "./ui/pages/ContactDetailPage";
import { ContactListPage } from "./ui/pages/ContactListPage";
import { ConversationPage } from "./ui/pages/ConversationPage";
import { InboxPage } from "./ui/pages/InboxPage";

export const conversationRoutes: RouteObject[] = [
  { path: "inbox", element: <InboxPage /> },
  { path: "inbox/:conversationId", element: <ConversationPage /> },
  { path: "contacts", element: <ContactListPage /> },
  { path: "contacts/:contactId", element: <ContactDetailPage /> },
];
