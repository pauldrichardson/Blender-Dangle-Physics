DANGLE PHYSICS v5.1
Lead Developer: Paul D. Richardson

Collaborator: Gemini

Compatibility: Blender 5.1+

1. GETTING STARTED
In Pose Mode, select your bones in order from the Base (root) to the Tip.

Click "Build Dangle Chain" in the Dangle tab (Sidebar).

The script creates Empties that your bones automatically track to create motion.

2. THE "FIRST LINK" STRATEGY
Note: The first bone in your selection is NOT affected by physics.

The Manual Override: This bone acts as your handle. By keyframing this first link, you "drive" the physics (e.g., swishing a tail back and forth). The rest of the chain reacts naturally to the momentum you create manually.

3. BASIC SETTINGS & CONTROLS
Stiffness: Controls how hard the bone tries to return to its original pose. Higher values make the chain "springy" or rigid.

Momentum: Controls the internal resistance of the chain's movement.

Gravity: Simulates a downward pull on the chain.

Apply to All Links: Use this to instantly sync your Stiffness, Momentum, and Gravity settings across every link in the active chain.

4. RECOMMENDED RECIPES
Heavy Chain: Stiffness 0.2, Momentum 0.9, Gravity 1.2.

Organic Tail: Stiffness 1.0, Momentum 0.8, Gravity 0.0.

Pro Tip (The Whip Effect): Counterintuitively, setting the end of the tail to a lower momentum setting will actually increase the "swing" or whip effect. For a natural "wag fade," try setting the tip Momentum to 0.3 and gradually increase it (0.4, 0.5...) as you move toward the base.

5. PAUSE OPTIONS
Pause All Dangles: A global toggle that stops all physics calculations across the entire scene. Perfect for posing or performance during heavy scenes.

Pause This Dangle: Stops physics only for the currently selected chain. Useful when you want one part of a character to remain static while others stay dynamic.

6. ENVIRONMENT & UI
Wind Force Field: Select a native Blender Wind Force Field (Shift+A > Force Field > Wind) from the dropdown. The physics will respond to the Strength and Noise settings of that field.

Mesh Colliders: Select any Mesh object to act as a solid barrier for the dangle chain.

Distance: Adjust this slider to create a "cushion" or padding around your collider mesh.

UI Navigation: Due to current API constraints, the eyedropper tool is not available for selection.

Navigation Hack: Use your Up/Down Arrow Keys to scroll through the object lists. The list "wraps around," meaning hitting Down at the bottom brings you back to the Top.

7. BAKING
The Main Benefit: Baking allows you to run the animation at full speed in the viewport without waiting for the CPU to calculate physics on every frame.

Bake This Dangle: Commits the motion to keyframes on the Empties for the active chain. This is useful for hand-tweaking the final motion or exporting to other software.

Unbake This Dangle: Removes the keyframes and restores the live, real-time physics simulation for the active chain.

Bake All / Unbake All: These buttons process every Dangle chain in the scene simultaneously. Unbake All is especially useful as a "reset" to clear all baked animation data from every Dangle object at once.

8. REMOVE DANGLE CHAIN
The Clean-Up Button: Use this to completely dismantle the system. It removes all constraints from your armature, deletes the helper Empties, and deletes the associated collection. It leaves your original armature exactly as it was before the Dangle was built.
