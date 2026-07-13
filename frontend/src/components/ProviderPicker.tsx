import { useEffect } from "react";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { useProviders } from "@/hooks/useApi";
import { useAppStore } from "@/store/appStore";

export function ProviderPicker() {
  const { data } = useProviders();
  const { provider, model, setProvider, setModel } = useAppStore();

  // Initialize provider/model defaults once providers load.
  useEffect(() => {
    if (!data || provider) return;
    const preferred =
      data.providers.find((p) => p.id === data.default_provider && p.available) ||
      data.providers.find((p) => p.available) ||
      data.providers[0];
    if (preferred) {
      setProvider(preferred.id);
      setModel(preferred.default_model);
    }
  }, [data, provider, setProvider, setModel]);

  if (!data) return null;

  const current = data.providers.find((p) => p.id === provider);

  return (
    <div className="space-y-2">
      <div>
        <label className="mb-1 block text-xs font-medium text-muted-foreground">
          Provider
        </label>
        <Select
          value={provider ?? undefined}
          onValueChange={(v) => {
            setProvider(v);
            const p = data.providers.find((x) => x.id === v);
            if (p) setModel(p.default_model);
          }}
        >
          <SelectTrigger className="h-8 text-xs">
            <SelectValue placeholder="Select provider" />
          </SelectTrigger>
          <SelectContent>
            {data.providers.map((p) => (
              <SelectItem key={p.id} value={p.id} disabled={!p.available}>
                {p.label}
                {!p.available ? " (no key)" : ""}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>

      {current && current.models.length > 0 && (
        <div>
          <label className="mb-1 block text-xs font-medium text-muted-foreground">
            Model
          </label>
          <Select value={model ?? undefined} onValueChange={setModel}>
            <SelectTrigger className="h-8 text-xs">
              <SelectValue placeholder="Select model" />
            </SelectTrigger>
            <SelectContent>
              {current.models.map((m) => (
                <SelectItem key={m} value={m}>
                  {m}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>
      )}
    </div>
  );
}
