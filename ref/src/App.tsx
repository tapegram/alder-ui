/*
 * shadcn/ui reference grid: the dev-only oracle that test/parity.py diffs alder-ui against.
 *
 * Every compared element carries data-ref="<component>/<variant>/<state-or-size>"
 * (optional data-ref-states="hover focus" lists the states the harness drives). Overlays
 * carry data-ref-open and are rendered open. The text is fixed so widths compare.
 *
 * Layout (ruling R1): the twin page, demo/parity.html, may not use <style> or style=; it lays
 * out with <al-page width="wide"> and <al-stack> only. So this page reproduces the twin's
 * containing blocks rather than the other way round:
 *   - the frame is al-page width="wide": max-width 80rem, border-box, margin-inline auto,
 *     padding 2rem 1rem, padding-inline 1.5rem from 40rem (Tailwind `sm`). At the harness's
 *     1280px viewport that is a 1232px content column (body margin 0).
 *   - sections stack like a column al-stack (flex column, children stretch), so block
 *     controls (inputs, textareas, cards, alerts, tables, tabs) are 1232px wide;
 *   - intrinsic controls (buttons, badges, checkboxes, select trigger, pagination) sit in
 *     row stacks (flex row, wrap, items-center) and keep their own width.
 * Overlays live in "stages" at the end so they cover no other marker (see OverlayStage).
 */
import { useEffect, useLayoutEffect, useRef, useState, type ReactNode } from "react"
import { ChevronRightIcon, InfoIcon, OctagonXIcon } from "lucide-react"
import { toast } from "sonner"

import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import {
  Card,
  CardAction,
  CardContent,
  CardDescription,
  CardFooter,
  CardHeader,
  CardTitle,
} from "@/components/ui/card"
import { Checkbox } from "@/components/ui/checkbox"
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog"
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import {
  Pagination,
  PaginationContent,
  PaginationEllipsis,
  PaginationItem,
  PaginationLink,
  PaginationNext,
  PaginationPrevious,
} from "@/components/ui/pagination"
import {
  Popover,
  PopoverContent,
  PopoverDescription,
  PopoverHeader,
  PopoverTitle,
  PopoverTrigger,
} from "@/components/ui/popover"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { Separator } from "@/components/ui/separator"
import { Toaster } from "@/components/ui/sonner"
import {
  Table,
  TableBody,
  TableCaption,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { Textarea } from "@/components/ui/textarea"
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from "@/components/ui/tooltip"

const noop = () => {}
const keepFocus = (e: Event) => e.preventDefault()

/* Markers on DOM that the shadcn components render themselves and give no prop for. */
const LATE_MARKERS: Array<[string, (root: Document) => Element | null | undefined]> = [
  ["table/wrapper/default", (d) => d.querySelector('[data-ref="table/table/default"]')?.parentElement],
  ["dialog/close/open", (d) => d.querySelector('[data-ref="dialog/content/open"] > [data-slot="dialog-close"]')],
  ["tooltip/arrow/open", (d) => d.querySelector('[data-ref="tooltip/content/open"] > span > svg')],
  ["toast/default/default", (d) => d.querySelector('[data-sonner-toast]:not([data-type]), [data-sonner-toast][data-type="default"]')],
  ["toast/success/default", (d) => d.querySelector('[data-sonner-toast][data-type="success"]')],
  ["toast/info/default", (d) => d.querySelector('[data-sonner-toast][data-type="info"]')],
  ["toast/warning/default", (d) => d.querySelector('[data-sonner-toast][data-type="warning"]')],
  ["toast/error/default", (d) => d.querySelector('[data-sonner-toast][data-type="error"]')],
]

/* Tags LATE_MARKERS as their nodes appear, then sets <html data-ref-ready> once every
   marker is tagged and the fonts have loaded, so the harness has one thing to wait for. */
function useLateMarkers() {
  useEffect(() => {
    let done = false
    const apply = () => {
      if (done) return
      let missing = 0
      for (const [ref, find] of LATE_MARKERS) {
        const el = find(document)
        if (!el) {
          missing++
          continue
        }
        if (el.getAttribute("data-ref") !== ref) el.setAttribute("data-ref", ref)
        const open = ref.startsWith("dialog/") || ref.startsWith("tooltip/")
        if (open && !el.hasAttribute("data-ref-open")) el.setAttribute("data-ref-open", "")
      }
      if (missing === 0) {
        done = true
        observer.disconnect()
        document.fonts.ready.then(() => document.documentElement.setAttribute("data-ref-ready", ""))
      }
    }
    const observer = new MutationObserver(apply)
    observer.observe(document.body, { childList: true, subtree: true, attributes: true })
    apply()
    return () => observer.disconnect()
  }, [])
}

/* `#dark` puts .dark on <html> (for humans; the harness toggles the class itself). */
function useHashTheme() {
  useEffect(() => {
    const sync = () => document.documentElement.classList.toggle("dark", location.hash === "#dark")
    sync()
    window.addEventListener("hashchange", sync)
    return () => window.removeEventListener("hashchange", sync)
  }, [])
}

/* Sonner's theme follows the <html> class, as next-themes would make it in an app. */
function useHtmlDark() {
  const [dark, setDark] = useState(() => document.documentElement.classList.contains("dark"))
  useEffect(() => {
    const html = document.documentElement
    const observer = new MutationObserver(() => setDark(html.classList.contains("dark")))
    observer.observe(html, { attributes: true, attributeFilter: ["class"] })
    return () => observer.disconnect()
  }, [])
  return dark
}

function Section({ name, children }: { name: string; children: ReactNode }) {
  return (
    <section className="flex flex-col gap-4" data-section={name}>
      <h2 className="text-sm font-medium text-muted-foreground">{name}</h2>
      {children}
    </section>
  )
}

/* A row al-stack: flex row, wrap, items centred, gap 0.5rem. */
function Row({ children }: { children: ReactNode }) {
  return <div className="flex flex-row flex-wrap items-center gap-2">{children}</div>
}

/* A field as in the shadcn form demos: grid gap-2 of Label, control, then help/error text. */
function Field({ children }: { children: ReactNode }) {
  return <div className="grid gap-2">{children}</div>
}

/*
 * OverlayStage: a box with a transform, so `position: fixed` inside it resolves against the
 * box instead of the viewport. The dialog is rendered non-modal (a modal Radix dialog traps
 * focus and sets pointer-events: none on <body>, which would stop the harness driving hover
 * and focus on every other marker), its portalled content node is moved into the stage after
 * mount, and the overlay that Radix renders only for modal dialogs is drawn here with the
 * same class string as shadcn's DialogOverlay. The recipe classes are untouched; only the
 * containing block changes. The stage is wider than 34rem, so the content keeps its
 * sm:max-w-lg (32rem) width, as it would against a 1280px viewport.
 */
function DialogStage() {
  const stage = useRef<HTMLDivElement>(null)
  useLayoutEffect(() => {
    const move = () => {
      const content = document.querySelector('[data-ref="dialog/content/open"]')
      if (content && stage.current && content.parentElement !== stage.current) {
        stage.current.appendChild(content)
      }
      return !!content
    }
    if (move()) return
    const observer = new MutationObserver(() => {
      if (move()) observer.disconnect()
    })
    observer.observe(document.body, { childList: true })
    return () => observer.disconnect()
  }, [])
  return (
    <div ref={stage} className="relative h-[22rem] overflow-hidden rounded-lg [transform:translateZ(0)]">
      {/* shadcn DialogOverlay, verbatim classes (Radix renders it only when modal). */}
      <div
        data-slot="dialog-overlay"
        data-state="open"
        data-ref="dialog/overlay/open"
        data-ref-open=""
        className="fixed inset-0 z-50 bg-black/50 data-[state=closed]:animate-out data-[state=closed]:fade-out-0 data-[state=open]:animate-in data-[state=open]:fade-in-0"
      />
      <Dialog open modal={false} onOpenChange={noop}>
        <DialogContent
          data-ref="dialog/content/open"
          data-ref-open=""
          onOpenAutoFocus={keepFocus}
          onCloseAutoFocus={keepFocus}
          onInteractOutside={keepFocus}
        >
          <DialogHeader>
            <DialogTitle data-ref="dialog/title/open">Dialog Title</DialogTitle>
            <DialogDescription data-ref="dialog/description/open">Dialog Description</DialogDescription>
          </DialogHeader>
          <DialogFooter data-ref="dialog/footer/open">
            <Button variant="outline">Cancel</Button>
            <Button>Continue</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  )
}

/* Popover, menu and tooltip are anchored to their triggers (Radix popper, fixed position,
   collision avoidance off so the side never flips); each cell reserves room for its overlay. */
function PopperStage() {
  return (
    <TooltipProvider>
      <div className="flex flex-row flex-wrap items-start gap-2">
        <div className="flex h-56 w-80 flex-col items-center">
          <Popover open onOpenChange={noop}>
            <PopoverTrigger asChild>
              <Button variant="outline">Open popover</Button>
            </PopoverTrigger>
            <PopoverContent
              data-ref="popover/content/open"
              data-ref-open=""
              avoidCollisions={false}
              onOpenAutoFocus={keepFocus}
              onInteractOutside={keepFocus}
            >
              <PopoverHeader>
                <PopoverTitle>Popover Title</PopoverTitle>
                <PopoverDescription>Popover Description</PopoverDescription>
              </PopoverHeader>
            </PopoverContent>
          </Popover>
        </div>
        <div className="flex h-56 w-80 flex-col items-center">
          <DropdownMenu open modal={false} onOpenChange={noop}>
            <DropdownMenuTrigger asChild>
              <Button variant="outline">Open menu</Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent
              data-ref="menu/content/open"
              data-ref-open=""
              avoidCollisions={false}
              onCloseAutoFocus={keepFocus}
              onInteractOutside={keepFocus}
            >
              <DropdownMenuItem data-ref="menu/item/open">Profile</DropdownMenuItem>
              <DropdownMenuItem>Settings</DropdownMenuItem>
              <DropdownMenuSeparator data-ref="menu/separator/open" />
              <DropdownMenuItem variant="destructive" data-ref="menu/item-destructive/open">
                Delete
              </DropdownMenuItem>
            </DropdownMenuContent>
          </DropdownMenu>
        </div>
        <div className="flex h-56 w-80 flex-col items-center justify-center">
          <Tooltip open onOpenChange={noop}>
            <TooltipTrigger asChild>
              <Button variant="outline">Hover</Button>
            </TooltipTrigger>
            <TooltipContent data-ref="tooltip/content/open" data-ref-open="" avoidCollisions={false}>
              Tooltip text
            </TooltipContent>
          </Tooltip>
        </div>
      </div>
    </TooltipProvider>
  )
}

/* Sonner renders in place (no portal), so its fixed <ol> resolves against this stage. */
function ToastStage() {
  const dark = useHtmlDark()
  useEffect(() => {
    const options = { duration: Infinity, description: "Toast description" }
    toast("Toast title", { ...options, id: "default" })
    toast.success("Toast title", { ...options, id: "success" })
    toast.info("Toast title", { ...options, id: "info" })
    toast.warning("Toast title", { ...options, id: "warning" })
    toast.error("Toast title", { ...options, id: "error" })
  }, [])
  return (
    <div className="relative h-[32rem] overflow-hidden rounded-lg bg-muted/50 [transform:translateZ(0)]">
      <Toaster expand visibleToasts={5} theme={dark ? "dark" : "light"} />
    </div>
  )
}

const VARIANTS = ["default", "destructive", "outline", "secondary", "ghost", "link"] as const

export default function App() {
  useHashTheme()
  useLateMarkers()

  return (
    <main className="mx-auto box-border w-full max-w-[80rem] px-4 py-8 sm:px-6">
      <div className="flex flex-col gap-10">
        <Section name="button">
          <Row>
            {VARIANTS.map((v) => (
              <Button key={v} variant={v} data-ref={`button/${v}/default`} data-ref-states="hover focus">
                Button
              </Button>
            ))}
          </Row>
          <Row>
            <Button size="xs" data-ref="button/default/xs">Button</Button>
            <Button size="sm" data-ref="button/default/sm">Button</Button>
            <Button size="lg" data-ref="button/default/lg">Button</Button>
            <Button size="icon" aria-label="Next" data-ref="button/default/icon">
              <ChevronRightIcon />
            </Button>
            <Button size="icon-sm" aria-label="Next" data-ref="button/default/icon-sm">
              <ChevronRightIcon />
            </Button>
            <Button size="icon-lg" aria-label="Next" data-ref="button/default/icon-lg">
              <ChevronRightIcon />
            </Button>
          </Row>
          <Row>
            <Button disabled data-ref="button/default/disabled">Button</Button>
            <Button data-ref="button/default/with-icon">
              <ChevronRightIcon />
              Button
            </Button>
          </Row>
        </Section>

        <Section name="input">
          <Field>
            <Label htmlFor="email" data-ref="label/default/default">Email</Label>
            <Input id="email" type="email" placeholder="Email" data-ref="input/default/default" data-ref-states="focus" />
            <p className="text-sm text-muted-foreground" data-ref="input/description/default">
              Enter your email address.
            </p>
          </Field>
          <Field>
            <Label htmlFor="email-disabled">Email</Label>
            <Input id="email-disabled" type="email" placeholder="Email" disabled data-ref="input/default/disabled" />
          </Field>
          <Field>
            <Label htmlFor="email-invalid">Email</Label>
            <Input id="email-invalid" type="email" placeholder="Email" aria-invalid="true" data-ref="input/default/invalid" />
            <p className="text-sm font-medium text-destructive" data-ref="input/error/default">
              Enter a valid email address.
            </p>
          </Field>
        </Section>

        <Section name="textarea">
          <Field>
            <Label htmlFor="message">Message</Label>
            <Textarea id="message" placeholder="Message" data-ref="textarea/default/default" />
          </Field>
          <Field>
            <Label htmlFor="message-invalid">Message</Label>
            <Textarea id="message-invalid" placeholder="Message" aria-invalid="true" data-ref="textarea/default/invalid" />
          </Field>
        </Section>

        <Section name="select">
          <Field>
            <Label htmlFor="fruit">Fruit</Label>
            <Select>
              <SelectTrigger id="fruit" data-ref="select/trigger/default">
                <SelectValue placeholder="Select a fruit" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="apple">Apple</SelectItem>
                <SelectItem value="banana">Banana</SelectItem>
              </SelectContent>
            </Select>
          </Field>
          <Field>
            <Label htmlFor="fruit-disabled">Fruit</Label>
            <Select disabled>
              <SelectTrigger id="fruit-disabled" data-ref="select/trigger/disabled">
                <SelectValue placeholder="Select a fruit" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="apple">Apple</SelectItem>
              </SelectContent>
            </Select>
          </Field>
        </Section>

        <Section name="checkbox">
          <div className="flex items-center gap-2">
            <Checkbox id="terms-1" data-ref="checkbox/default/unchecked" />
            <Label htmlFor="terms-1">Accept terms</Label>
          </div>
          <div className="flex items-center gap-2">
            <Checkbox id="terms-2" defaultChecked data-ref="checkbox/default/checked" />
            <Label htmlFor="terms-2">Accept terms</Label>
          </div>
          <div className="flex items-center gap-2">
            <Checkbox id="terms-3" disabled data-ref="checkbox/default/disabled" />
            <Label htmlFor="terms-3">Accept terms</Label>
          </div>
          <div className="flex items-center gap-2">
            <Checkbox id="terms-4" aria-invalid="true" data-ref="checkbox/default/invalid" />
            <Label htmlFor="terms-4">Accept terms</Label>
          </div>
        </Section>

        <Section name="card">
          <Card data-ref="card/root/default">
            <CardHeader>
              <CardTitle data-ref="card/title/default">Card Title</CardTitle>
              <CardDescription data-ref="card/description/default">Card Description</CardDescription>
              <CardAction data-ref="card/action/default">Card Action</CardAction>
            </CardHeader>
            <CardContent data-ref="card/content/default">
              <p>Card Content</p>
            </CardContent>
            <CardFooter data-ref="card/footer/default">
              <p>Card Footer</p>
            </CardFooter>
          </Card>
        </Section>

        <Section name="badge">
          <Row>
            <Badge data-ref="badge/default/default">Badge</Badge>
            <Badge variant="secondary" data-ref="badge/secondary/default">Badge</Badge>
            <Badge variant="destructive" data-ref="badge/destructive/default">Badge</Badge>
            <Badge variant="outline" data-ref="badge/outline/default">Badge</Badge>
          </Row>
        </Section>

        <Section name="alert">
          <Alert data-ref="alert/default/root">
            <InfoIcon data-ref="alert/default/icon" />
            <AlertTitle data-ref="alert/default/title">Alert Title</AlertTitle>
            <AlertDescription data-ref="alert/default/description">Alert Description</AlertDescription>
          </Alert>
          <Alert variant="destructive" data-ref="alert/destructive/root">
            <OctagonXIcon data-ref="alert/destructive/icon" />
            <AlertTitle data-ref="alert/destructive/title">Alert Title</AlertTitle>
            <AlertDescription data-ref="alert/destructive/description">Alert Description</AlertDescription>
          </Alert>
        </Section>

        <Section name="table">
          <Table data-ref="table/table/default">
            <TableCaption data-ref="table/caption/default">A list of your recent invoices.</TableCaption>
            <TableHeader>
              <TableRow>
                <TableHead data-ref="table/head/default">Invoice</TableHead>
                <TableHead>Status</TableHead>
                <TableHead>Method</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              <TableRow data-ref="table/row/default">
                <TableCell data-ref="table/cell/default">INV001</TableCell>
                <TableCell>Paid</TableCell>
                <TableCell>Credit Card</TableCell>
              </TableRow>
              <TableRow data-ref="table/row/hover" data-ref-states="hover">
                <TableCell>INV002</TableCell>
                <TableCell>Pending</TableCell>
                <TableCell>PayPal</TableCell>
              </TableRow>
              <TableRow>
                <TableCell>INV003</TableCell>
                <TableCell>Unpaid</TableCell>
                <TableCell>Bank Transfer</TableCell>
              </TableRow>
            </TableBody>
          </Table>
        </Section>

        <Section name="pagination">
          <Pagination>
            <PaginationContent>
              <PaginationItem>
                <PaginationPrevious href="#" data-ref="pagination/previous/default" />
              </PaginationItem>
              <PaginationItem>
                <PaginationLink href="#" data-ref="pagination/link/default">1</PaginationLink>
              </PaginationItem>
              <PaginationItem>
                <PaginationLink href="#" isActive data-ref="pagination/active/default">2</PaginationLink>
              </PaginationItem>
              <PaginationItem>
                <PaginationLink href="#">3</PaginationLink>
              </PaginationItem>
              <PaginationItem>
                <PaginationEllipsis />
              </PaginationItem>
              <PaginationItem>
                <PaginationNext href="#" data-ref="pagination/next/default" />
              </PaginationItem>
            </PaginationContent>
          </Pagination>
        </Section>

        <Section name="tabs">
          <Tabs defaultValue="account">
            <TabsList data-ref="tabs/list/default">
              <TabsTrigger value="account" data-ref="tabs/trigger-active/default">Account</TabsTrigger>
              <TabsTrigger value="password" data-ref="tabs/trigger/default">Password</TabsTrigger>
            </TabsList>
            <TabsContent value="account" data-ref="tabs/content/default">Tab Content</TabsContent>
            <TabsContent value="password">Password Content</TabsContent>
          </Tabs>
          <Tabs defaultValue="account">
            <TabsList variant="line" data-ref="tabs/list/line">
              <TabsTrigger value="account" data-ref="tabs/trigger-active/line">Account</TabsTrigger>
              <TabsTrigger value="password">Password</TabsTrigger>
            </TabsList>
            <TabsContent value="account">Tab Content</TabsContent>
            <TabsContent value="password">Password Content</TabsContent>
          </Tabs>
        </Section>

        <Section name="typography">
          {/* Raw elements with the docs' Typography classes (Ref §3); `hr` is the Separator and
              the table uses the shadcn Table recipe, as alder-ui maps them (design spec §7). */}
          <div>
            <h1 className="scroll-m-20 text-4xl font-extrabold tracking-tight text-balance" data-ref="typography/h1/default">
              Heading One
            </h1>
            <h2 className="scroll-m-20 border-b pb-2 text-3xl font-semibold tracking-tight first:mt-0" data-ref="typography/h2/default">
              Heading Two
            </h2>
            <h3 className="scroll-m-20 text-2xl font-semibold tracking-tight" data-ref="typography/h3/default">
              Heading Three
            </h3>
            <h4 className="scroll-m-20 text-xl font-semibold tracking-tight" data-ref="typography/h4/default">
              Heading Four
            </h4>
            <p className="leading-7 [&:not(:first-child)]:mt-6" data-ref="typography/p/default">
              A paragraph of body text.
            </p>
            <p className="leading-7 [&:not(:first-child)]:mt-6">
              Run{" "}
              <code
                className="relative rounded bg-muted px-[0.3rem] py-[0.2rem] font-mono text-sm font-semibold"
                data-ref="typography/code/default"
              >
                alder build
              </code>{" "}
              then read the{" "}
              <a href="#" className="font-medium text-primary underline underline-offset-4" data-ref="typography/a/default">
                guide
              </a>
              .
            </p>
            <blockquote className="mt-6 border-l-2 pl-6 italic" data-ref="typography/blockquote/default">
              A quoted passage.
            </blockquote>
            <ul className="my-6 ml-6 list-disc [&>li]:mt-2" data-ref="typography/ul/default">
              <li data-ref="typography/li/default">First item</li>
              <li>Second item</li>
            </ul>
            <Separator data-ref="typography/hr/default" />
            <table className="w-full caption-bottom text-sm" data-ref="typography/table/default">
              <thead className="[&_tr]:border-b">
                <tr className="border-b transition-colors hover:bg-muted/50 has-aria-expanded:bg-muted/50 data-[state=selected]:bg-muted">
                  <th
                    className="h-10 px-2 text-left align-middle font-medium whitespace-nowrap text-foreground [&:has([role=checkbox])]:pr-0 [&>[role=checkbox]]:translate-y-[2px]"
                    data-ref="typography/th/default"
                  >
                    Name
                  </th>
                  <th className="h-10 px-2 text-left align-middle font-medium whitespace-nowrap text-foreground [&:has([role=checkbox])]:pr-0 [&>[role=checkbox]]:translate-y-[2px]">
                    Value
                  </th>
                </tr>
              </thead>
              <tbody className="[&_tr:last-child]:border-0">
                <tr className="border-b transition-colors hover:bg-muted/50 has-aria-expanded:bg-muted/50 data-[state=selected]:bg-muted">
                  <td
                    className="p-2 align-middle whitespace-nowrap [&:has([role=checkbox])]:pr-0 [&>[role=checkbox]]:translate-y-[2px]"
                    data-ref="typography/td/default"
                  >
                    Alpha
                  </td>
                  <td className="p-2 align-middle whitespace-nowrap [&:has([role=checkbox])]:pr-0 [&>[role=checkbox]]:translate-y-[2px]">
                    One
                  </td>
                </tr>
                <tr className="border-b transition-colors hover:bg-muted/50 has-aria-expanded:bg-muted/50 data-[state=selected]:bg-muted">
                  <td className="p-2 align-middle whitespace-nowrap [&:has([role=checkbox])]:pr-0 [&>[role=checkbox]]:translate-y-[2px]">
                    Beta
                  </td>
                  <td className="p-2 align-middle whitespace-nowrap [&:has([role=checkbox])]:pr-0 [&>[role=checkbox]]:translate-y-[2px]">
                    Two
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
        </Section>

        <Section name="dialog">
          <DialogStage />
        </Section>

        <Section name="popover, menu, tooltip">
          <PopperStage />
        </Section>

        <Section name="toast">
          <ToastStage />
        </Section>
      </div>
    </main>
  )
}
