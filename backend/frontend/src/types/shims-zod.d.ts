// TEMP shim for Zod — remove after real deps are installed.
// Purpose: allow `import { z } from "zod"` and `z.infer` to typecheck.

declare module "zod" {
	// minimal surface used by our code
	namespace z {
		// pretend schema type
		type ZodTypeAny = unknown;
		// allow `z.infer<typeof Schema>`
		type infer<T> = any;
	}

	// allow `import { z } from "zod"`
	const z: {
		// very small API to satisfy usage; all types are `any` to avoid pollution
		object: (...args: any[]) => any;
		array: (...args: any[]) => any;
		string: (...args: any[]) => any;
		number: (...args: any[]) => any;
		boolean: (...args: any[]) => any;
		unknown: (...args: any[]) => any;
		literal: (...args: any[]) => any;
		enum: (...args: any[]) => any;
		union: (...args: any[]) => any;
		optional: (...args: any[]) => any;
		record: (...args: any[]) => any;
		// expose types namespace
		infer: z.infer<any>;
		ZodTypeAny: z.ZodTypeAny;
		// safeParse used in api.ts
		// (schemas created above will carry `.safeParse`)
	};

	export { z };
}
// TEMP shim; remove after npm install
declare module "zod";
