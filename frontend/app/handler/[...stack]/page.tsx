import { stackServerApp } from "@/stack";
import { StackHandler } from "@stackframe/stack";

export default function Handler(props: any) {
    return <StackHandler app={stackServerApp} {...props} />;
}
