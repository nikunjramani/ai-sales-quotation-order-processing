import type { RouteObject } from "react-router";

import { ChannelsPage } from "./ui/pages/ChannelsPage";

export const channelRoutes: RouteObject[] = [{ path: "channels", element: <ChannelsPage /> }];
