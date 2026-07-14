import { useEffect } from "react";
import {
  ScrollSelect,
  ScrollSelectContent,
  ScrollSelectItem,
  ScrollSelectTrigger,
} from "@/components/ui/scroll-select";
import { useProviders } from "@/hooks/useApi";
import { useAppStore } from "@/store/appStore";
import { cn } from "@/lib/utils";

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
        <ScrollSelect
          value={provider ?? undefined}
          onValueChange={(v) => {
            setProvider(v);
            const p = data.providers.find((x) => x.id === v);
            if (p) setModel(p.default_model);
          }}
        >
          <ScrollSelectTrigger className="h-8 text-xs">
            <span className={cn(!current && "text-muted-foreground")}>
              {current ? current.label : "Select provider"}
            </span>
          </ScrollSelectTrigger>
          <ScrollSelectContent>
            {data.providers.map((p) => (
              <ScrollSelectItem key={p.id} value={p.id} disabled={!p.available}>
                {p.label}
                {!p.available ? " (no key)" : ""}
              </ScrollSelectItem>
            ))}
          </ScrollSelectContent>
        </ScrollSelect>
      </div>

      {current && current.models.length > 0 && (
        <div>
          <label className="mb-1 block text-xs font-medium text-muted-foreground">
            Model
          </label>
          <ScrollSelect value={model ?? undefined} onValueChange={setModel}>
            <ScrollSelectTrigger className="h-8 text-xs">
              <span className={cn(!model && "text-muted-foreground")}>
                {model || "Select model"}
              </span>
            </ScrollSelectTrigger>
            <ScrollSelectContent>
              {current.models.map((m) => (
                <ScrollSelectItem key={m} value={m}>
                  {m}
                </ScrollSelectItem>
              ))}
            </ScrollSelectContent>
          </ScrollSelect>
        </div>
      )}
    </div>
  );
}
