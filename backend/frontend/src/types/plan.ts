export type DurationSec = number;

export interface Scene {
  id?: string;
  image_prompt?: string;
  narration?: string;
  duration_sec?: DurationSec;
  [k: string]: any;
}

export interface PlanHeader {
  title?: string;
  description?: string;
  aspect_ratio?: "16:9" | "9:16" | "1:1";
  duration_sec?: DurationSec;
  [k: string]: any;
}

export interface Plan {
  header?: PlanHeader;
  scenes: Scene[];
  template_id?: string | number;
  [k: string]: any;
}

export interface InputField {
  key: string;
  label?: string;
  type?: "text" | "number" | "textarea" | "select";
  required?: boolean;
  placeholder?: string;
  options?: string[];
}

export type InputsSchema = {
  [key: string]: {
    type: 'string' | 'number' | 'boolean';
    enum?: string[];
    title?: string;
    description?: string;
  }
};
