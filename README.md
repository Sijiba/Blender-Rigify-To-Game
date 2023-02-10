# Blender Rigify To Game
 This script gives you the power to turn your cool Rigify rig into something
 you can actually use in games. This script:
  * Creates an easier-to-export duplicate of your Rigify character
  * Fixes vertex groups of parts that auto-rigging shouldn't deform
  * Removes "DEF-" from all the vertex weights so the copied Metarig's bones can shine
  * Removes a list of excess bones and transfers their mesh weights to proper parents
  * Applies the Multiresolution modifier at its current LOD and keeps all your shapekeys
       (this part takes a hot minute so you can disable it)
	   
 Load the script in Blender, fill out the first parameter chunk and you're good to go