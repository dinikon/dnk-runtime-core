import type {VariantProps} from "class-variance-authority"
import {cva} from "class-variance-authority"

export {default as CustomButton} from "./Button.vue"

export const customButtonVariants = cva(
    [
        "relative inline-flex shrink-0 items-center justify-center gap-1.5 overflow-hidden whitespace-nowrap",
        "border border-transparent font-medium outline-none transition-colors",
        "disabled:pointer-events-none disabled:cursor-not-allowed",
        "[&_svg]:pointer-events-none [&_svg]:size-3.5 [&_svg]:shrink-0",
    ],
    {
        variants: {
            variant: {
                primary: "",
                secondary: "",
                tertiary: "",
            },
            accent: {
                default: "",
                blue: "",
                danger: "",
            },
            size: {
                small: "h-6 min-w-6 px-2 text-[12px] leading-4",
                medium: "h-8 min-w-8 px-3 text-[13px] leading-5",
            },
            position: {
                standalone: "rounded",
                left: "rounded-l rounded-r-none",
                middle: "-ml-px rounded-none",
                right: "-ml-px rounded-l-none rounded-r",
            },
            fullWidth: {
                true: "w-full",
                false: "",
            },
            inverted: {
                true: "",
                false: "",
            },
            focus: {
                true: "ring-2 ring-offset-1",
                false: "focus-visible:ring-2 focus-visible:ring-offset-1",
            },
        },
        compoundVariants: [
            {
                variant: "primary",
                accent: "default",
                inverted: false,
                class: "bg-[#141414] text-white hover:bg-[#2b2b2b] active:bg-[#3d3d3d] disabled:bg-[#d9d9d9] disabled:text-[#8f8f8f] ring-[#141414]/30",
            },
            {
                variant: "primary",
                accent: "blue",
                inverted: false,
                class: "bg-[#1961ed] text-white hover:bg-[#2d72f3] active:bg-[#0f4ec6] disabled:bg-[#d7e4ff] disabled:text-[#7a9fe5] ring-[#1961ed]/30",
            },
            {
                variant: "primary",
                accent: "danger",
                inverted: false,
                class: "bg-[#d92d20] text-white hover:bg-[#e5483d] active:bg-[#b42318] disabled:bg-[#f7d7d4] disabled:text-[#d98c86] ring-[#d92d20]/30",
            },
            {
                variant: "secondary",
                accent: "default",
                inverted: false,
                class: "border-[#d9d9d9] bg-white text-[#141414] hover:bg-[#f5f5f5] active:bg-[#ededed] disabled:border-[#eeeeee] disabled:bg-white disabled:text-[#b3b3b3] ring-[#141414]/20",
            },
            {
                variant: "secondary",
                accent: "blue",
                inverted: false,
                class: "border-[#b9cdfd] bg-white text-[#1961ed] hover:bg-[#eef4ff] active:bg-[#dce9ff] disabled:border-[#d7e4ff] disabled:text-[#9bb7ed] ring-[#1961ed]/25",
            },
            {
                variant: "secondary",
                accent: "danger",
                inverted: false,
                class: "border-[#f2b8b5] bg-white text-[#d92d20] hover:bg-[#fff1f0] active:bg-[#ffe3e0] disabled:border-[#f7d7d4] disabled:text-[#d98c86] ring-[#d92d20]/25",
            },
            {
                variant: "tertiary",
                accent: "default",
                inverted: false,
                class: "bg-transparent text-[#5f6368] hover:bg-[#f2f4f7] active:bg-[#e7e9ec] disabled:text-[#b3b3b3] ring-[#141414]/20",
            },
            {
                variant: "tertiary",
                accent: "blue",
                inverted: false,
                class: "bg-transparent text-[#1961ed] hover:bg-[#eef4ff] active:bg-[#dce9ff] disabled:text-[#9bb7ed] ring-[#1961ed]/25",
            },
            {
                variant: "tertiary",
                accent: "danger",
                inverted: false,
                class: "bg-transparent text-[#d92d20] hover:bg-[#fff1f0] active:bg-[#ffe3e0] disabled:text-[#d98c86] ring-[#d92d20]/25",
            },
            {
                variant: "primary",
                inverted: true,
                class: "bg-white text-[#141414] hover:bg-white/90 active:bg-white/80 disabled:bg-white/20 disabled:text-white/45 ring-white/40",
            },
            {
                variant: "secondary",
                inverted: true,
                class: "border-white/35 bg-white/10 text-white hover:bg-white/20 active:bg-white/25 disabled:border-white/15 disabled:text-white/45 ring-white/35",
            },
            {
                variant: "tertiary",
                inverted: true,
                class: "bg-transparent text-white hover:bg-white/15 active:bg-white/20 disabled:text-white/45 ring-white/35",
            },
        ],
        defaultVariants: {
            variant: "primary",
            accent: "default",
            size: "medium",
            position: "standalone",
            fullWidth: false,
            inverted: false,
            focus: false,
        },
    },
)

export type CustomButtonVariants = VariantProps<typeof customButtonVariants>
export type CustomButtonVariant = NonNullable<CustomButtonVariants["variant"]>
export type CustomButtonAccent = NonNullable<CustomButtonVariants["accent"]>
export type CustomButtonSize = NonNullable<CustomButtonVariants["size"]>
export type CustomButtonPosition = NonNullable<CustomButtonVariants["position"]>
