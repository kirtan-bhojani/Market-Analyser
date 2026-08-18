import type { ParamSchema } from "../../hooks/useStrategies";

interface SchemaParamFormProps {
  schema: ParamSchema;
  values: Record<string, number>;
  onChange: (values: Record<string, number>) => void;
}

/** Renders a numeric input for every property in a preset's JSON param schema.
 * Integer params step by 1, floats by 0.1; minimum/maximum are enforced natively. */
export function SchemaParamForm({ schema, values, onChange }: SchemaParamFormProps) {
  return (
    <div className="param-form">
      {Object.entries(schema.properties).map(([key, spec]) => (
        <label className="pf-field" key={key} htmlFor={`param-${key}`}>
          <span className="pf-label">{key}</span>
          <input
            id={`param-${key}`}
            className="pf-input num"
            aria-label={key}
            type="number"
            step={spec.type === "integer" ? 1 : 0.1}
            min={spec.minimum}
            max={spec.maximum}
            value={values[key] ?? spec.default ?? 0}
            onChange={(e) => onChange({ ...values, [key]: Number(e.target.value) })}
          />
        </label>
      ))}
    </div>
  );
}
