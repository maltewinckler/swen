/**
 * Dashboard Customizer
 *
 * Modal for enabling/disabling and reordering dashboard widgets.
 * Uses @dnd-kit for smooth animated drag-and-drop.
 */

import { useState, useEffect } from 'react'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { GripVertical, Check, LayoutGrid, RotateCcw, X } from 'lucide-react'
import { Button, Spinner, Modal, ModalHeader, ModalBody, ModalFooter } from '@/components/ui'
import { updateDashboardSettings, resetDashboardSettings } from '@/api/preferences'
import { WIDGET_REGISTRY, getWidgetsByCategory } from './widgets'
import { cn, arraysEqual } from '@/lib/utils'
import type { DashboardSettings } from '@/api/preferences'

// @dnd-kit imports
import {
  DndContext,
  closestCenter,
  KeyboardSensor,
  PointerSensor,
  useSensor,
  useSensors,
  DragOverlay,
} from '@dnd-kit/core'
import type { DragEndEvent, DragStartEvent } from '@dnd-kit/core'
import {
  arrayMove,
  SortableContext,
  sortableKeyboardCoordinates,
  useSortable,
  rectSortingStrategy,
} from '@dnd-kit/sortable'
// CSS is from @dnd-kit/utilities (unused but kept for reference)

interface DashboardCustomizerProps {
  isOpen: boolean
  onClose: () => void
  currentSettings: DashboardSettings
}

// Sortable widget item component
function SortableWidgetItem({
  widgetId,
  onRemove,
}: {
  widgetId: string
  onRemove: (id: string) => void
}) {
  const widget = WIDGET_REGISTRY[widgetId]
  const isFullWidth = widget?.colSpan === 2

  const {
    attributes,
    listeners,
    setNodeRef,
    transform,
    transition,
    isDragging,
  } = useSortable({ id: widgetId })

  // Only apply Y translation for movement, ignore X scaling that distorts full-width items
  const style: React.CSSProperties = {
    transform: transform
      ? `translate3d(${transform.x}px, ${transform.y}px, 0)`
      : undefined,
    transition,
    opacity: isDragging ? 0.4 : 1,
    zIndex: isDragging ? 50 : 'auto' as const,
    // Prevent text distortion during transforms
    willChange: 'transform',
    backfaceVisibility: 'hidden' as const,
  }

  if (!widget) return null

  return (
    <div
      ref={setNodeRef}
      style={style}
      {...attributes}
      {...listeners}
      className={cn(
        'flex items-center gap-2 p-3 rounded-lg border',
        'bg-accent-primary/5 border-accent-primary/30',
        'select-none touch-none',
        'cursor-grab active:cursor-grabbing',
        isFullWidth && 'col-span-2',
        isDragging && 'ring-2 ring-accent-primary shadow-lg scale-[1.02]',
      )}
    >
      <GripVertical className="h-4 w-4 text-text-muted flex-shrink-0" />
      <div className="flex-1 min-w-0 overflow-hidden">
        <div className="flex items-center gap-2">
          <p className="text-sm font-medium text-text-primary truncate">
            {widget.title}
          </p>
          {isFullWidth && (
            <span className="text-[10px] px-1.5 py-0.5 rounded bg-accent-primary/20 text-accent-primary font-medium whitespace-nowrap flex-shrink-0">
              Full width
            </span>
          )}
        </div>
        <p className="text-xs text-text-muted truncate">
          {widget.description}
        </p>
      </div>
      <Button
        variant="ghost"
        size="sm"
        onClick={(e) => {
          e.stopPropagation()
          onRemove(widgetId)
        }}
        onPointerDown={(e) => e.stopPropagation()}
        className="flex-shrink-0"
      >
        <X className="h-4 w-4" />
      </Button>
    </div>
  )
}

// Overlay shown while dragging
function DragOverlayItem({ widgetId }: { widgetId: string }) {
  const widget = WIDGET_REGISTRY[widgetId]
  const isFullWidth = widget?.colSpan === 2

  if (!widget) return null

  return (
    <div
      style={{
        // Fixed width to prevent any distortion
        width: isFullWidth ? 'calc(var(--grid-width, 600px) - 0.5rem)' : 'calc((var(--grid-width, 600px) - 0.5rem) / 2)',
        maxWidth: isFullWidth ? '100%' : '50%',
      }}
      className={cn(
        'flex items-center gap-2 p-3 rounded-lg border',
        'bg-bg-surface border-accent-primary',
        'shadow-2xl ring-2 ring-accent-primary',
        'cursor-grabbing',
        'transform-gpu',
      )}
    >
      <GripVertical className="h-4 w-4 text-accent-primary flex-shrink-0" />
      <div className="flex-1 min-w-0 overflow-hidden">
        <div className="flex items-center gap-2">
          <p className="text-sm font-medium text-text-primary truncate">
            {widget.title}
          </p>
          {isFullWidth && (
            <span className="text-[10px] px-1.5 py-0.5 rounded bg-accent-primary/20 text-accent-primary font-medium whitespace-nowrap flex-shrink-0">
              Full width
            </span>
          )}
        </div>
        <p className="text-xs text-text-muted truncate">
          {widget.description}
        </p>
      </div>
      <div className="w-8 flex-shrink-0" /> {/* Placeholder for button */}
    </div>
  )
}

export default function DashboardCustomizer({
  isOpen,
  onClose,
  currentSettings,
}: DashboardCustomizerProps) {
  const queryClient = useQueryClient()

  // Local state for editing
  const [enabledWidgets, setEnabledWidgets] = useState<string[]>([])
  const [activeId, setActiveId] = useState<string | null>(null)

  // Initialize from props
  useEffect(() => {
    setEnabledWidgets([...currentSettings.enabled_widgets])
  }, [currentSettings.enabled_widgets])

  // Configure sensors for drag detection
  const sensors = useSensors(
    useSensor(PointerSensor, {
      activationConstraint: {
        distance: 8, // Minimum drag distance before activating
      },
    }),
    useSensor(KeyboardSensor, {
      coordinateGetter: sortableKeyboardCoordinates,
    })
  )

  // Update mutation
  const updateMutation = useMutation({
    mutationFn: updateDashboardSettings,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['preferences', 'dashboard'] })
      onClose()
    },
  })

  // Reset mutation
  const resetMutation = useMutation({
    mutationFn: resetDashboardSettings,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['preferences', 'dashboard'] })
      onClose()
    },
  })

  const isLoading = updateMutation.isPending || resetMutation.isPending

  // Toggle widget (add/remove)
  const toggleWidget = (widgetId: string) => {
    setEnabledWidgets((prev) =>
      prev.includes(widgetId)
        ? prev.filter((id) => id !== widgetId)
        : [...prev, widgetId]
    )
  }

  // Handle drag start
  const handleDragStart = (event: DragStartEvent) => {
    setActiveId(event.active.id as string)
  }

  // Handle drag end - reorder items
  const handleDragEnd = (event: DragEndEvent) => {
    const { active, over } = event
    setActiveId(null)

    if (over && active.id !== over.id) {
      setEnabledWidgets((items) => {
        const oldIndex = items.indexOf(active.id as string)
        const newIndex = items.indexOf(over.id as string)
        return arrayMove(items, oldIndex, newIndex)
      })
    }
  }

  // Save changes
  const handleSave = () => {
    updateMutation.mutate({ enabled_widgets: enabledWidgets })
  }

  // Reset to defaults
  const handleReset = () => {
    resetMutation.mutate()
  }

  // Check if changes were made (shallow comparison is sufficient for string arrays)
  const hasChanges = !arraysEqual(enabledWidgets, currentSettings.enabled_widgets)

  const widgetsByCategory = getWidgetsByCategory()

  return (
    <Modal isOpen={isOpen} onClose={onClose} size="2xl">
      <ModalHeader
        onClose={onClose}
        description="Enable widgets and drag to reorder"
      >
        <div className="flex items-center gap-2">
          <LayoutGrid className="h-5 w-5 text-accent-primary" />
          Customize Dashboard
        </div>
      </ModalHeader>

      <ModalBody>
          {/* Enabled widgets - sortable grid */}
          {enabledWidgets.length > 0 && (
            <div className="mb-6">
              <h3 className="text-sm font-medium text-text-primary mb-3">
                Enabled Widgets
                <span className="text-text-muted font-normal ml-2">
                  (drag to reorder)
                </span>
              </h3>
              <DndContext
                sensors={sensors}
                collisionDetection={closestCenter}
                onDragStart={handleDragStart}
                onDragEnd={handleDragEnd}
              >
                <SortableContext
                  items={enabledWidgets}
                  strategy={rectSortingStrategy}
                >
                  <div
                    className="grid grid-cols-2 gap-2"
                    style={{ '--grid-width': '100%' } as React.CSSProperties}
                  >
                    {enabledWidgets.map((widgetId) => (
                      <SortableWidgetItem
                        key={widgetId}
                        widgetId={widgetId}
                        onRemove={toggleWidget}
                      />
                    ))}
                  </div>
                </SortableContext>
                <DragOverlay dropAnimation={{
                  duration: 200,
                  easing: 'cubic-bezier(0.18, 0.67, 0.6, 1.22)',
                }}>
                  {activeId ? <DragOverlayItem widgetId={activeId} /> : null}
                </DragOverlay>
              </DndContext>
            </div>
          )}

          {/* Available widgets by category */}
          {Object.entries(widgetsByCategory).map(([category, widgets]) => {
            const availableWidgets = widgets.filter(
              (w) => !enabledWidgets.includes(w.id)
            )
            if (availableWidgets.length === 0) return null

            return (
              <div key={category} className="mb-6">
                <h3 className="text-sm font-medium text-text-primary mb-3 capitalize">
                  {category} Widgets
                </h3>
                <div className="grid grid-cols-2 gap-2">
                  {availableWidgets.map((widget) => {
                    const isFullWidth = widget.colSpan === 2
                    return (
                      <button
                        key={widget.id}
                        onClick={() => toggleWidget(widget.id)}
                        className={cn(
                          'flex items-center gap-2 p-3 rounded-lg border text-left transition-all',
                          'border-border-default hover:border-accent-primary/50',
                          'hover:bg-accent-primary/5',
                          isFullWidth && 'col-span-2',
                        )}
                      >
                        <div className="flex-1 min-w-0">
                          <div className="flex items-center gap-2">
                            <p className="text-sm font-medium text-text-primary truncate">
                              {widget.title}
                            </p>
                            {isFullWidth && (
                              <span className="text-[10px] px-1.5 py-0.5 rounded bg-text-muted/20 text-text-muted font-medium whitespace-nowrap">
                                Full width
                              </span>
                            )}
                          </div>
                          <p className="text-xs text-text-muted truncate">
                            {widget.description}
                          </p>
                        </div>
                        <Check className="h-4 w-4 text-transparent" />
                      </button>
                    )
                  })}
                </div>
              </div>
            )
          })}
      </ModalBody>

      <ModalFooter className="justify-between">
        <Button
          variant="ghost"
          size="sm"
          onClick={handleReset}
          disabled={isLoading}
          className="text-text-muted hover:text-text-secondary"
        >
          <RotateCcw className="h-4 w-4 mr-2" />
          Reset to Defaults
        </Button>
        <div className="flex items-center gap-2">
          <Button variant="secondary" onClick={onClose} disabled={isLoading}>
            Cancel
          </Button>
          <Button
            onClick={handleSave}
            disabled={!hasChanges || isLoading}
          >
            {isLoading ? <Spinner size="sm" className="mr-2" /> : null}
            Save Changes
          </Button>
        </div>
      </ModalFooter>
    </Modal>
  )
}
