export type RingikPose =
  | 'neutral'
  | 'peeking'
  | 'waving'
  | 'sitting'
  | 'pointing'
  | 'sad'
  | 'hiding'
  | 'surprised'
  | 'gift'
  | 'phone';

export type RingikPlacement = 'fixed-bottom-right' | 'fixed-top-right' | 'absolute';

export type RingikProps = {
  pose: RingikPose;
  message?: string;
  placement: RingikPlacement;
  className?: string;
  bubbleAlign?: 'center' | 'left' | 'right';
  bubblePlacement?: 'top' | 'left' | 'right';
  onClick?: () => void;
  clickable?: boolean;
  visible?: boolean;
  showMessage?: boolean;
};
