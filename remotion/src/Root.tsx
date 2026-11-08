import React from "react";
import { Composition } from "remotion";
import { Main } from "./Main";
import { FPS, TOTAL } from "./lib";

export const Root: React.FC = () => (
  <Composition id="Main" component={Main} durationInFrames={Math.ceil(TOTAL * FPS)} fps={FPS} width={1080} height={1920} />
);
