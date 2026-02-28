import { useEffect, useRef, useImperativeHandle, forwardRef } from 'react';
import { createPluginUI } from 'molstar/lib/mol-plugin-ui';
import { renderReact18 } from 'molstar/lib/mol-plugin-ui/react18';
import { DefaultPluginUISpec } from 'molstar/lib/mol-plugin-ui/spec';
import type { PluginUIContext } from 'molstar/lib/mol-plugin-ui/context';
import { PluginConfig } from 'molstar/lib/mol-plugin/config';
import 'molstar/lib/mol-plugin-ui/skin/light.scss';

export interface MolstarViewerHandle {
  getPlugin: () => PluginUIContext | null;
}

const MolstarViewer = forwardRef<MolstarViewerHandle>(function MolstarViewer(_props, ref) {
  const containerRef = useRef<HTMLDivElement>(null);
  const pluginRef = useRef<PluginUIContext | null>(null);

  useImperativeHandle(ref, () => ({
    getPlugin: () => pluginRef.current,
  }));

  useEffect(() => {
    let disposed = false;

    async function init() {
      if (!containerRef.current) return;

      const plugin = await createPluginUI({
        target: containerRef.current,
        spec: {
          ...DefaultPluginUISpec(),
          layout: {
            initial: {
              showControls: false,
              isExpanded: false,
            },
          },
          config: [
            [PluginConfig.VolumeStreaming.Enabled, false],
            [PluginConfig.Viewport.ShowAnimation, false],
          ],
        },
        render: renderReact18,
      });

      if (disposed) {
        plugin.dispose();
        return;
      }

      pluginRef.current = plugin;
    }

    init();

    return () => {
      disposed = true;
      pluginRef.current?.dispose();
      pluginRef.current = null;
    };
  }, []);

  return (
    <div
      ref={containerRef}
      className="w-full h-full"
      style={{ position: 'relative' }}
    />
  );
});

export default MolstarViewer;
